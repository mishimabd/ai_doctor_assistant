import re
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from groq import Groq
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
client = Groq(api_key="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")
cyrillic_pattern = re.compile(r'[^\u0400-\u04FF\s.,!?:;\'"()🔴-]')


async def call_groq_api(messages: list) -> str:
    system_message = {
        "role": "system",
        "content": "Ты виртуальный ассистент в медицинской клинике. "
                   "Отвечай только на русском языке. Ответ должен быть на чистом русском, без использования символов "
                   "или букв из других языков (например, китайских, японских, английских). "
                   "Отвечай на вопросы только связанные с медициной и здоровьем пациентов, другие вопросы не принимай, "
                   "скажи, что ты не специализируешься в этом. "
                   "Ты помогаешь докторам с вопросами о здоровье их пациентов. "
                   "Укажи болезнь, разделив её линиями '🔴БОЛЕЗНЬ🔴'.\n"
                   "После этого укажи, что следует посоветовать пациенту, также разделив советы линиями '🔴СОВЕТЫ🔴'. "
                   "Перед отправкой своего ответа, обязательно проверь, чтобы все твои слова были на русском языке "
                   "и не содержали никаких символов или букв из других языков."
                   "Задавай встречные вопросы под конец, чтобы получить больше информации от доктора. 1-2 предложения."
                   "Отвечай очень детально и давай полный ответ по поводу болезни и того, что следует сделать."
                   "Отвечай очень структурно и по-человечески, избегая сложных или неуместных символов."
                   "Делай большой акцент на том, что ты помогаешь докторам в лечении пациентов. Перенаправь их к докторам по их болезням."
    }

    try:
        conversation_with_system_message = [system_message] + messages

        chat_completion = client.chat.completions.create(
            messages=conversation_with_system_message,
            model="llama-3.1-70b-versatile"
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return "Извините, я не смог обработать ваш запрос."


async def ai_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    logger.info(f"Received message: {user_message}")

    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    if user_message == "Очистить историю 🗑️":
        await clear_history(update, context)
        return

    context.user_data["conversation_history"].append({
        "role": "user",
        "content": user_message
    })

    # Send a temporary loading message
    loading_message = await update.message.reply_text("🤖 Генерация ответа, пожалуйста, подождите...")

    while True:
        ai_response = await call_groq_api(context.user_data["conversation_history"])
        logger.info(f"AI response: {ai_response}")

        if not cyrillic_pattern.search(ai_response):
            break
        logger.info("Detected non-Cyrillic characters in the AI response. Regenerating response...")

    context.user_data["conversation_history"].append({
        "role": "assistant",
        "content": ai_response
    })

    await context.bot.edit_message_text(text=ai_response, chat_id=update.message.chat_id,
                                        message_id=loading_message.message_id)


async def ai_assistant_respond(update: Update, context) -> None:
    assistant_message = (
        "Здравствуйте! Я ваш виртуальный ассистент.🏥\n"
        "Я здесь, чтобы помочь вам с вопросами о ваших пациентах.🩺\n"
        "Дайте детальные объяснения состояния пациента, буду рад на них ответить!"
    )
    await update.message.reply_text(assistant_message)


async def start_button(update: Update, context: CallbackContext) -> None:
    context.user_data["is_text_for_adding"] = False
    user = update.message.from_user
    buttons = [
        [KeyboardButton("Виртуальный ассистент 🤖")],
        [KeyboardButton("Как пользоваться ботом 📖")],
        [KeyboardButton("Очистить историю 🗑️")],  # New button for clearing history
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(
        f"👋Добрый день, {user.first_name}! Я ваш виртуальный ассистент! Задавайте ваши интересующие вопросы",
        reply_markup=reply_markup, parse_mode="HTML"
    )


async def clear_history(update: Update, context: CallbackContext) -> None:
    context.user_data["conversation_history"] = []
    await update.message.reply_text("Запись памяти была очищена! Задавайте ваши вопросы.")
