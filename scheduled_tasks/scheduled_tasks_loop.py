import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv

from assistant import send_message


load_dotenv()


logging.basicConfig(
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	level=logging.INFO,
)
logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
	id: int
	task_name: str
	task_payload: str | None
	schedule_type: str
	cron_expression: str | None
	interval_value: int | None
	interval_unit: str | None
	created_at: str | None


def _get_db_path() -> str:
	db_path = os.getenv("ASSISTANT_DB")
	if not db_path:
		raise ValueError("Environment variable ASSISTANT_DB is not set.")
	return db_path


def _fetch_active_tasks() -> list[ScheduledTask]:
	conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
	cur = conn.cursor()
	cur.execute(
		"""
		SELECT
			id,
			task_name,
			task_payload,
			schedule_type,
			cron_expression,
			interval_value,
			interval_unit,
			created_at
		FROM scheduled_tasks
		WHERE is_active = 1
		ORDER BY id ASC
		"""
	)
	rows = cur.fetchall()
	cur.close()
	conn.close()

	return [
		ScheduledTask(
			id=row[0],
			task_name=row[1],
			task_payload=row[2],
			schedule_type=row[3],
			cron_expression=row[4],
			interval_value=row[5],
			interval_unit=row[6],
			created_at=row[7],
		)
		for row in rows
	]


def _parse_created_at(created_at: str | None) -> datetime:
	if not created_at:
		return datetime.now()

	try:
		return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
	except ValueError:
		logger.warning("Invalid created_at format: %s. Using current time.", created_at)
		return datetime.now()


def _interval_seconds(value: int | None, unit: str | None) -> int | None:
	if value is None or value <= 0 or unit is None:
		return None

	if unit == "second":
		return value
	if unit == "minute":
		return value * 60
	if unit == "hour":
		return value * 60 * 60
	if unit == "day":
		return value * 60 * 60 * 24

	return None


def _parse_cron_field(field: str, minimum: int, maximum: int) -> set[int]:
	values: set[int] = set()

	for chunk in field.split(","):
		chunk = chunk.strip()
		if not chunk:
			continue

		if "/" in chunk:
			base, step_text = chunk.split("/", 1)
			step = int(step_text)
			if step <= 0:
				raise ValueError("Invalid step in cron field.")

			if base == "*":
				start = minimum
				end = maximum
			elif "-" in base:
				start_text, end_text = base.split("-", 1)
				start = int(start_text)
				end = int(end_text)
			else:
				start = int(base)
				end = maximum

			if start < minimum or end > maximum or start > end:
				raise ValueError("Invalid range in cron field.")

			values.update(range(start, end + 1, step))
			continue

		if chunk == "*":
			values.update(range(minimum, maximum + 1))
			continue

		if "-" in chunk:
			start_text, end_text = chunk.split("-", 1)
			start = int(start_text)
			end = int(end_text)
			if start < minimum or end > maximum or start > end:
				raise ValueError("Invalid range in cron field.")
			values.update(range(start, end + 1))
			continue

		value = int(chunk)
		if value < minimum or value > maximum:
			raise ValueError("Value out of bounds in cron field.")
		values.add(value)

	if not values:
		raise ValueError("Cron field does not contain any valid values.")

	return values


def _cron_matches(cron_expression: str | None, now: datetime) -> bool:
	if not cron_expression:
		return False

	parts = cron_expression.split()
	if len(parts) != 5:
		logger.warning("Cron expression must have 5 fields: %s", cron_expression)
		return False

	try:
		minute_values = _parse_cron_field(parts[0], 0, 59)
		hour_values = _parse_cron_field(parts[1], 0, 23)
		day_values = _parse_cron_field(parts[2], 1, 31)
		month_values = _parse_cron_field(parts[3], 1, 12)
		weekday_values = _parse_cron_field(parts[4], 0, 7)
	except ValueError:
		logger.warning("Invalid cron expression: %s", cron_expression)
		return False

	if 7 in weekday_values:
		weekday_values.add(0)
		weekday_values.discard(7)

	cron_weekday = (now.weekday() + 1) % 7

	day_is_wildcard = parts[2] == "*"
	weekday_is_wildcard = parts[4] == "*"
	day_matches = now.day in day_values
	weekday_matches = cron_weekday in weekday_values

	if day_is_wildcard and weekday_is_wildcard:
		day_or_weekday_matches = True
	elif day_is_wildcard:
		day_or_weekday_matches = weekday_matches
	elif weekday_is_wildcard:
		day_or_weekday_matches = day_matches
	else:
		day_or_weekday_matches = day_matches or weekday_matches

	return (
		now.minute in minute_values
		and now.hour in hour_values
		and now.month in month_values
		and day_or_weekday_matches
	)


def _run_scheduled_task(task: ScheduledTask) -> None:
	message = task.task_payload if task.task_payload else task.task_name
	logger.info("Executing scheduled task id=%s name=%s", task.id, task.task_name)
	send_message(message)


def run_scheduled_tasks_loop(poll_interval_seconds: int = 1) -> None:
	"""Run scheduled tasks continuously based on cron/interval definitions."""
	logger.info("Scheduled tasks loop started.")

	last_run_by_task: dict[int, datetime] = {}
	last_cron_minute_by_task: dict[int, str] = {}

	while True:
		now = datetime.now()
		try:
			tasks = _fetch_active_tasks()

			for task in tasks:
				if task.schedule_type == "interval":
					every_seconds = _interval_seconds(task.interval_value, task.interval_unit)
					if every_seconds is None:
						logger.warning(
							"Skipping invalid interval task id=%s name=%s",
							task.id,
							task.task_name,
						)
						continue

					last_run = last_run_by_task.get(task.id, _parse_created_at(task.created_at))
					elapsed_seconds = (now - last_run).total_seconds()

					if elapsed_seconds >= every_seconds:
						_run_scheduled_task(task)
						last_run_by_task[task.id] = now
					continue

				if task.schedule_type == "cron":
					current_minute_key = now.strftime("%Y-%m-%d %H:%M")
					already_ran_this_minute = (
						last_cron_minute_by_task.get(task.id) == current_minute_key
					)

					if not already_ran_this_minute and _cron_matches(task.cron_expression, now):
						_run_scheduled_task(task)
						last_cron_minute_by_task[task.id] = current_minute_key
					continue

				logger.warning(
					"Skipping task with unknown schedule_type id=%s schedule_type=%s",
					task.id,
					task.schedule_type,
				)

			active_task_ids = {task.id for task in tasks}
			last_run_by_task = {
				task_id: last_run
				for task_id, last_run in last_run_by_task.items()
				if task_id in active_task_ids
			}
			last_cron_minute_by_task = {
				task_id: minute_key
				for task_id, minute_key in last_cron_minute_by_task.items()
				if task_id in active_task_ids
			}
		except Exception as exc:
			logger.exception("Scheduled tasks loop iteration failed.", exc_info=exc)

		time.sleep(max(1, poll_interval_seconds))


def _read_poll_interval() -> int:
	raw_value = os.getenv("SCHEDULED_TASKS_POLL_INTERVAL_SECONDS", "1")
	try:
		value = int(raw_value)
		if value <= 0:
			raise ValueError
		return value
	except ValueError:
		logger.warning(
			"Invalid SCHEDULED_TASKS_POLL_INTERVAL_SECONDS=%s. Using default 1.",
			raw_value,
		)
		return 1


if __name__ == "__main__":
	run_scheduled_tasks_loop(poll_interval_seconds=_read_poll_interval())
