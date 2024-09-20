import re
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from groq import Groq
import logging
import psycopg2
from utils import save_phone_to_db, get_phone_number_from_db, save_user_to_db, is_phone_number_in_whitelist, \
    decrement_message_limit

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
client = Groq(api_key="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")
cyrillic_pattern = re.compile(r'[^\u0400-\u04FF\s.,!?:;\'"()🔴-]')

conn = psycopg2.connect(
    dbname="virtual_assistant_database",
    user="postgres",
    password="Lg26y0M@x",
    host="91.147.92.32",
)

USER_DATA = {}


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
    user_id = update.message.from_user.id
    phone_number = get_phone_number_from_db(user_id)

    if phone_number is None:
        await update.message.reply_text(
            "Пожалуйста, поделитесь вашим номером телефона, нажав на кнопку ниже, чтобы продолжить использование бота."
        )
        return

    if not is_phone_number_in_whitelist(phone_number):
        await update.message.reply_text(
            "Пожалуйста, свяжитесь с менеджером, чтобы вас добавили в белый список.",
        )
        return

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
    remaining_limit = decrement_message_limit(user_id)

    # Check if the user has reached their limit
    if remaining_limit == 0:
        await update.message.reply_text(
            "Вы достигли лимита использования бота. Пожалуйста, свяжитесь с поддержкой для дальнейших действий."
        )
        return
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


# Updated start_button function
async def start_button(update: Update, context: CallbackContext) -> None:
    context.user_data["is_text_for_adding"] = False
    user = update.message.from_user

    # Save user's Telegram ID and username to the database
    save_user_to_db(user.id, user.username)

    # Define the buttons for the bot's reply
    buttons = [
        [KeyboardButton("Виртуальный ассистент 🤖")],
        [KeyboardButton("Как пользоваться ботом 📖")],
        [KeyboardButton("Очистить историю 🗑️")],
        [KeyboardButton("Калькулятор ИМТ 🏋️")],
        [KeyboardButton("Поделиться номером телефона 📞", request_contact=True)],
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    # Reply with a greeting message
    await update.message.reply_text(
        f"👋Добрый день, {user.first_name}! Я ваш виртуальный ассистент! Задавайте ваши интересующие вопросы",
        reply_markup=reply_markup, parse_mode="HTML"
    )

async def ask_weight(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    context.user_data["is_bmi_active"] = True  # Set BMI active flag to True when button is pressed
    USER_DATA[user.id] = {}  # Initialize user data for BMI
    await update.message.reply_text("Пожалуйста, введите ваш вес в килограммах (например, 70):")

# Function to handle BMI inputs for both weight and height (height in centimeters)
async def handle_bmi_input(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_input = update.message.text

    if not context.user_data.get("is_bmi_active", False):
        # If BMI is not active, let the AI assistant handle it
        await ai_assistant(update, context)
        return

    # Proceed with BMI logic if the flag is set to True
    if "weight" not in USER_DATA[user_id]:
        try:
            weight = float(user_input)
            USER_DATA[user_id]["weight"] = weight
            await update.message.reply_text("Теперь введите ваш рост в сантиметрах (например, 175):")
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректное значение веса.")
    else:
        try:
            height_cm = float(user_input)
            USER_DATA[user_id]["height"] = height_cm

            weight = USER_DATA[user_id]["weight"]
            if height_cm <= 0:
                await update.message.reply_text("Пожалуйста, введите положительное значение роста.")
                return

            # Convert height from centimeters to meters
            height_m = height_cm / 100.0

            # Calculate BMI
            bmi = calculate_bmi(weight, height_m)
            category = bmi_category(bmi)

            # Reset BMI flag after calculation is complete
            context.user_data["is_bmi_active"] = False

            # Respond with the BMI result
            await update.message.reply_text(f"Ваш ИМТ: {bmi:.2f}\nКатегория: {category}")
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите корректное значение роста.")

# BMI calculation functions
def calculate_bmi(weight, height):
    """ Calculate BMI from weight (kg) and height (m). """
    return weight / (height ** 2)

def bmi_category(bmi):
    """ Determine the BMI category based on the calculated BMI. """
    if bmi < 18.5:
        return "Недостаточный вес"
    elif 18.5 <= bmi < 24.9:
        return "Нормальный вес"
    elif 25 <= bmi < 29.9:
        return "Избыточный вес"
    else:
        return "Ожирение"

async def clear_history(update: Update, context: CallbackContext) -> None:
    context.user_data["conversation_history"] = []
    await update.message.reply_text("Запись памяти была очищена! Задавайте ваши вопросы.")


async def contact_handler(update: Update, context: CallbackContext) -> None:
    user_contact = update.message.contact
    phone_number = user_contact.phone_number
    user_id = update.message.from_user.id

    await save_phone_to_db(user_id, phone_number)

    await update.message.reply_text("Спасибо, ваш номер телефона был сохранён!")


async def close_connection() -> None:
    if conn:
        conn.close()
