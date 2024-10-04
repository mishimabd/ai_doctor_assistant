import os
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Get the photo
    photo = update.message.photo[-1]  # Get the highest resolution photo
    file = await context.bot.get_file(photo.file_id)

    # Download the image as a byte array (no need to save on disk)
    image_data = await file.download_as_bytearray()

    # Send the image to the prediction endpoint
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field('file', image_data, filename='image.jpg')  # Adjust the filename if needed

        async with session.post('http://91.147.92.32:9999/predict', data=form_data) as response:
            if response.status == 200:
                json_response = await response.json()

                # Extract the relevant fields
                predicted_description = json_response.get('predicted_class_description', 'Описание недоступно')
                confidence = json_response.get('confidence', 'Неизвестно')

                # Formulate a more conversational response
                readable_message = (
                    f"🔍 *Ваш анализ готов!*\n\n"
                    f"На основании предоставленного изображения:\n\n"
                    f"- Мы обнаружили: *{predicted_description}*.\n"
                    f"- Уверенность в этом результате составляет *{confidence}*.\n\n"
                    f"Спасибо, что доверяете нам для анализа ваших данных! Если у вас есть вопросы, пожалуйста, обращайтесь."
                )
                await update.message.reply_text(readable_message, parse_mode='Markdown')
            else:
                await update.message.reply_text("Извините, произошла ошибка при анализе изображения. Пожалуйста, попробуйте снова.")

    return ConversationHandler.END  # End the conversation


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Обработка отменена.")
    return ConversationHandler.END


async def ecg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from main import WAITING_FOR_IMAGE
    assistant_message = (
        "Отправьте пожалуйста фото ЭКГ (жкг). Вот пример фотки: 🏥"
    )
    photo_path = "example.jpeg"  # Replace with the actual path to your photo

    # Send the message and the example photo
    await update.message.reply_text(assistant_message)
    await update.message.reply_photo(open(photo_path, 'rb'))

    return WAITING_FOR_IMAGE
