import logging

from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Runs on /start
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! This is LTA Smart Agent. One day I'll be able to answer your queries about anything transport related!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Runs on /help
    await update.message.reply_text("I can't do anything yet! Come back later?")


async def normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Echoes user message
    await update.message.reply_text("Hi! I'm not smart enough to reply you yet...")


def main() -> None:
    # Placeholder, bot token to be put in secrets of whatever hosting service we choose
    TELEGRAM_TOKEN = "placeholder"

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, normal_message)
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
