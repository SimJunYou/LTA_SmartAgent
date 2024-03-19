import os
import re
import dotenv

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from langchain_interface import LangchainInterface
from custom_logger import logger


LC_INTERFACE = LangchainInterface()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs on /start. Initializes LangChain interface instance and keeps it in user data."""
    user_id = f"{update.effective_user.username}[{update.effective_user.id}]"
    logger.info(f"User {user_id} starts session")

    # Initialize chat history and activity for this user
    context.user_data["history"] = []
    context.user_data["activity"] = True

    await update.message.reply_html(
        rf"Hi {update.effective_user.first_name}! This is RouteWise, your friendly route planner assistant. Feel free to ask me anything!"
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs on /stop. Stops and clears user data from the bot."""
    user_id = f"{update.effective_user.username}[{update.effective_user.id}]"

    logger.info(f"User {user_id} ends session")
    context.user_data["history"] = []
    context.user_data["activity"] = False


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs on /help"""
    await update.message.reply_text("I can't do anything yet! Come back later?")


async def normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs on any new message. Retrieve new query and history then pass them to Langchain"""

    user_id = f"{update.effective_user.username}[{update.effective_user.id}]"
    if "activity" not in context.user_data or not context.user_data["activity"]:
        await update.message.reply_text(
            "Hi there, please use /start so that I can help you!"
        )
        logger.warning(f"User {user_id} did not start bot but tried sending message")
        return

    placeholder_msg = await update.message.reply_text("Thinking...")
    user_message = update.message.text
    chat_history = context.user_data["history"]
    answer, new_history = LC_INTERFACE.query_agent(user_message, chat_history)
    logger.info(f"User {user_id} queries: {user_message}")

    # Update history
    context.user_data["history"] = new_history

    clean_answer = escape_markdown(answer)

    # Reply to the user
    await placeholder_msg.delete()
    await update.message.reply_text(clean_answer, parse_mode=ParseMode.MARKDOWN_V2)


def escape_markdown(text):
    """Escape special characters in the LLM's replies for Telegram's Markdown formatting."""
    escape_chars = r"\[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def main() -> None:
    dotenv.load_dotenv()
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_API_KEY")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, normal_message)
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
