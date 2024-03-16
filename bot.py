import os
import logging
import dotenv
from collections import defaultdict

from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from langchain_interface import LangchainInterface

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
conversation_history = defaultdict(list)


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
    user_id = update.effective_user.id
    user_message = update.message.text

    # Update conversation history for the user
    conversation_history[user_id].append(user_message)

    # Create a combined prompt with the conversation history
    combined_prompt = "\n".join(conversation_history[user_id])

    # Forward the combined prompt to Langchain
    answer = lc.query_agent(combined_prompt)

    # Reply to the user
    await update.message.reply_text(answer)

    # Limit the length of the conversation history to prevent it from growing indefinitely.
    max_history_length = 10
    if len(conversation_history[user_id]) > max_history_length:
        conversation_history[user_id].pop(0)  # Remove the oldest message


lc = LangchainInterface()


def main() -> None:
    dotenv.load_dotenv()
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_API_KEY")

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
