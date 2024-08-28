from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from groq import Groq
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key="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")


async def call_groq_api(messages: list) -> str:
    # System message to guide the AI's responses
    system_message = {
        "role": "system",
        "content": "Ты виртуальный ассистент в медицинской клинике. "
                   "Отвечай только на русском, без символов, без английских слов! "
                   "Отвечай на вопросы, только связанные с медициной, и с здоровьями пациентов, другие вопросы не "
                   "принимай, скажи что ты не специализируешь в этом. "
                   "Ты помогаешь докторам с вопросами о здоровье их пациентов. "
                   "Укажите болезнь, разделив её линиями '🔴БОЛЕЗНЬ🔴'.\n"
                   "После этого укажите, что следует посоветовать пациенту, также разделив советы линиями '🔴СОВЕТЫ🔴'. "
                   "Перед отправкой своего ответа, обязательно проверь, что бы все твои слова были на русском."
    }

    try:
        # Add system message at the beginning of the conversation history
        conversation_with_system_message = [system_message] + messages

        chat_completion = client.chat.completions.create(
            messages=conversation_with_system_message,
            model="llama-3.1-70b-versatile"
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling Groq API: {e}")
        return "Sorry, I couldn't process your request."


# Define the Telegram bot function
async def ai_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    logger.info(f"Received message: {user_message}")

    # Retrieve conversation history from user_data
    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    if user_message.lower() == "/clear":
        await clear_history(update, context)
        return

    # Append user message to conversation history
    context.user_data["conversation_history"].append({
        "role": "user",
        "content": user_message
    })

    # Get the response from the AI
    ai_response = await call_groq_api(context.user_data["conversation_history"])
    logger.info(f"AI response: {ai_response}")

    # Append AI response to conversation history
    context.user_data["conversation_history"].append({
        "role": "assistant",
        "content": ai_response
    })

    await update.message.reply_text(ai_response)


async def ai_assistant_respond(update: Update, context) -> None:
    assistant_message = (
        "Здравствуйте! Я ваш виртуальный ассистент.🏥\n"
        "Я здесь, чтобы помочь вам с вопросами о ваших пациентах.🩺\n"
        "Дайте детальные объяснения состояния пациента, буду рад на них ответить!\n"
        "Вы можете прописать /clear, чтобы я забыл прошлые сообщения."
    )
    await update.message.reply_text(assistant_message)


async def under_development(update: Update, context) -> None:
    under_development_message = "Я в разработке...🛠"
    await update.message.reply_text(under_development_message)


async def start_button(update: Update, context: CallbackContext) -> None:
    context.user_data["is_text_for_adding"] = False
    user = update.message.from_user
    buttons = [
        [KeyboardButton("Виртуальный ассистент 🤖")],
        [KeyboardButton("Как пользоваться ботом 📖")],
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text(
        f"👋Добрый день, {user.first_name}! Я ваш виртуальный ассистент! Задавайте ваши интересующие вопросы",
        reply_markup=reply_markup, parse_mode="HTML"
    )


async def clear_history(update: Update, context: CallbackContext) -> None:
    context.user_data["conversation_history"] = []
    await update.message.reply_text("Запись памяти была очищена! Задавайте ваши вопросы.")