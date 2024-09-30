import os
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler



async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Get the photo
    photo = update.message.photo[-1]  # Get the highest resolution photo
    file = await context.bot.get_file(photo.file_id)

    # Download the image
    file_path = await file.download_to_drive()  # This will download the file to a temporary path

    # Send the image to the prediction endpoint
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as image_file:
            form_data = aiohttp.FormData()
            form_data.add_field('file', image_file, filename='image.jpg')  # Adjust the filename if needed
            async with session.post('http://backend:9999/predict', data=form_data) as response:
                if response.status == 200:
                    json_response = await response.json()
                    await update.message.reply_text(f"Результат анализа: {json_response}")
                else:
                    await update.message.reply_text("Ошибка при отправке изображения для анализа.")

    # Clean up the downloaded file if needed
    os.remove(file_path)

    return ConversationHandler.END  # End the conversation


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Обработка отменена.")
    return ConversationHandler.END


async def ecg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from main import WAITING_FOR_IMAGE
    assistant_message = (
        "Отправьте пожалуйста фото ЭКГ. 🏥"
    )
    await update.message.reply_text(assistant_message)
    return WAITING_FOR_IMAGE