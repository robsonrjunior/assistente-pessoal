import logging
import os
from typing import Set

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from assistant import send_message


load_dotenv()


logger = logging.getLogger(__name__)


def _parse_allowed_users(raw_allowed_users: str | None) -> Set[int]:
	"""Parse ALLOWED_USERS from .env into a set of Telegram user IDs."""
	if not raw_allowed_users:
		return set()

	raw_allowed_users = raw_allowed_users.strip()
	if not raw_allowed_users:
		return set()

	if raw_allowed_users.startswith("[") and raw_allowed_users.endswith("]"):
		raw_allowed_users = raw_allowed_users[1:-1]

	allowed_users: Set[int] = set()
	for raw_user in raw_allowed_users.split(","):
		clean_user = raw_user.strip().strip('"').strip("'")
		if not clean_user:
			continue
		try:
			allowed_users.add(int(clean_user))
		except ValueError:
			logger.warning("Invalid ID in ALLOWED_USERS ignored: %s", clean_user)

	return allowed_users


ALLOWED_USERS = _parse_allowed_users(os.getenv("ALLOWED_USERS"))


def _is_allowed_user(update: Update) -> bool:
	"""Return True when sender is authorized to receive bot responses."""
	if update.effective_user is None:
		return False

	if not ALLOWED_USERS:
		return True

	if update.effective_user.id in ALLOWED_USERS:
		return True

	logger.info(
		"Unauthorized user tried to use the bot. user_id=%s",
		update.effective_user.id,
	)
	return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Handle /start command."""
	if not update.message or not _is_allowed_user(update):
		return

	await update.message.reply_text(
		"Oi! Eu sou seu assistente. Me envie uma mensagem para conversar."
	)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Handle incoming user messages and relay to the assistant core."""
	if not update.message or not update.message.text:
		return

	if not _is_allowed_user(update):
		return

	user_text = update.message.text

	try:
		assistant_response = send_message(user_text)
		await update.message.reply_text(assistant_response)
	except Exception as exc:
		logger.exception("Error while processing message in Telegram gateway", exc_info=exc)
		await update.message.reply_text(
			"Desculpe, ocorreu um erro ao processar sua mensagem."
		)


def run_telegram_gateway() -> None:
	"""Start Telegram bot polling loop."""
	bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
	if not bot_token:
		raise ValueError("Environment variable TELEGRAM_BOT_TOKEN is not set.")

	if ALLOWED_USERS:
		logger.info("Telegram gateway running with allowed-users filter. Total allowed: %d", len(ALLOWED_USERS))
	else:
		logger.info("ALLOWED_USERS is empty: bot will respond to any user.")

	application = Application.builder().token(bot_token).build()
	application.add_handler(CommandHandler("start", start))
	application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

	logger.info("Telegram gateway started with polling.")
	application.run_polling()


if __name__ == "__main__":
	run_telegram_gateway()
