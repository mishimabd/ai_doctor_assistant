import re

from openai import OpenAI
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, CallbackContext
import logging
from utils import save_phone_to_db, save_user_to_db

USER_DATA = {}
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Set your OpenAI API key
client = OpenAI(api_key="")

async def call_gpt_api(messages: list) -> str:
    system_message = {
        "role": "system",
        "content": (
        "Ты виртуальный ассистент в медицинской клинике. "
        "Отвечай только на вопросы, связанные с медициной и здоровьем пациентов, другие вопросы не принимай. "
        "Если вопрос выходит за пределы твоей специализации, сообщи, что ты не можешь помочь с этим, и перенаправь пациента к соответствующему специалисту. "
        "Ты помогаешь докторам с анализом состояния их пациентов, чтобы предоставить точные и подробные рекомендации."
        "После этого тщательно опиши симптомы и их возможные причины, основываясь на научных фактах и медицинских данных."
        "Объясняй все шаги и советы подробно, чтобы доктор получил полную картину и рекомендации по возможным действиям."
        "Убедись, что всё написано структурировано и понятно, избегая излишней медицинской терминологии, если она не требуется."
        "Не забывай уточнять, если для дальнейшего анализа или лечения нужно больше информации от пациента, и всегда задавай встречные вопросы, чтобы уточнить детали."
        "Отвечай в ясном и доступном стиле, используй короткие абзацы и избегай сложных фраз. "
        "Подробно объясни всё, что касается болезни, и помоги доктору в лечении. "
        "Помни, что твоя цель — помочь доктору максимально эффективно решить проблему пациента."
    )
    }

    try:
        conversation_with_system_message = [system_message] + messages

        # Call the API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation_with_system_message
        )

        # Use attribute access for the ChatCompletion object
        ai_response_content = response.choices[0].message.content
        return ai_response_content

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return "Извините, я не смог обработать ваш запрос."


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["conversation_history"] = []
    await update.message.reply_text("История сообщений была очищена! 🗑️")


async def ai_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_message = update.message.text

    logger.info(f"Received message from {user_id}: {user_message}")

    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    if user_message == "Очистить историю 🗑️":
        await clear_history(update, context)
        return

    context.user_data["conversation_history"].append({
        "role": "user",
        "content": user_message
    })

    loading_message = await update.message.reply_text("Отправьте вашу картинку!")
    return
    ai_response = await call_gpt_api(context.user_data["conversation_history"])
    logger.info(f"AI response: {ai_response}")

    context.user_data["conversation_history"].append({
        "role": "assistant",
        "content": ai_response
    })

    await context.bot.edit_message_text(
        text=ai_response,
        chat_id=update.message.chat_id,
        message_id=loading_message.message_id
    )


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
    save_user_to_db(user.id, user.username)
    buttons = [
        # [KeyboardButton("Виртуальный ассистент 🤖")],
        # [KeyboardButton("Как пользоваться ботом 📖")],
        # [KeyboardButton("Очистить историю 🗑️")],
        # [KeyboardButton("Калькулятор ИМТ 🏋️")],
        # [KeyboardButton("Калькулятор СКФ 🦠")],
        # [KeyboardButton("Анализ ЭКГ")],
        # [KeyboardButton("Анализ МРТ")],
        [KeyboardButton("Анализ рентгена легких")],
        # [KeyboardButton("Анализ фото")],
        # [KeyboardButton("Поделиться номером телефона 📞", request_contact=True)],
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await update.message.reply_text(
        f"👋Добрый день, {user.first_name}!",
        reply_markup=reply_markup, parse_mode="HTML"
    )


async def clear_history(update: Update, context: CallbackContext) -> None:
    context.user_data["conversation_history"] = []
    await update.message.reply_text("Запись памяти была очищена! Задавайте ваши вопросы.")


async def contact_handler(update: Update, context: CallbackContext) -> None:
    user_contact = update.message.contact
    phone_number = user_contact.phone_number
    user_id = update.message.chat_id

    await save_phone_to_db(user_id, phone_number)

    await update.message.reply_text("Спасибо, ваш номер телефона был сохранён!")
