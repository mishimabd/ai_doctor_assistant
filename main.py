from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from ai_assistent import ai_assistant, start_button, ai_assistant_respond


TELEGRAM_BOT_TOKEN = "7448334585:AAFFk55-y678noEyPqc6o_eDKIwwHeGWArk"
def main():
    print(f"{datetime.now()} - Started")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_button))
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex("^(Виртуальный ассистент 🤖)$"), ai_assistant_respond))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_assistant))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
