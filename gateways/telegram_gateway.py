import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from assistant import send_message


load_dotenv()


logging.basicConfig(
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Handle /start command."""
	await update.message.reply_text(
		"Oi! Eu sou seu assistente. Me envie uma mensagem para conversar."
	)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Handle incoming user messages and relay to the assistant core."""
	if not update.message or not update.message.text:
		return

	user_text = update.message.text

	try:
		assistant_response = send_message(user_text)
		await update.message.reply_text(assistant_response)
	except Exception as exc:
		logger.exception("Erro ao processar mensagem no gateway Telegram", exc_info=exc)
		await update.message.reply_text(
			"Desculpe, ocorreu um erro ao processar sua mensagem."
		)


def run_telegram_gateway() -> None:
	"""Start Telegram bot polling loop."""
	bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
	if not bot_token:
		raise ValueError("Variavel de ambiente TELEGRAM_BOT_TOKEN nao foi definida.")

	application = Application.builder().token(bot_token).build()
	application.add_handler(CommandHandler("start", start))
	application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

	logger.info("Gateway do Telegram iniciado com polling.")
	application.run_polling()


if __name__ == "__main__":
	run_telegram_gateway()
