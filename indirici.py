import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler
)
from telegram.ext import filters
import yt_dlp
import os
import time

# Durum tanımları (ConversationHandler için)
FORMAT_SELECTION, URL_WAITING = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

# Sabit klavye
reply_keyboard = [
    ['MP3', 'Video'],
    ['Yardım', 'Start'],
    ['Cancel']
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Video mu, MP3 mü indirelim? 😊\n"
        "Aşağıdaki butonlardan birini seç, hemen başlayalım!",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
    )
    return FORMAT_SELECTION

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba, ben senin indirme yardımcın! İşte yapabileceklerim:\n"
        "- TikTok, YouTube, Instagram Reels, X.com’dan video veya MP3 indirebilirim.\n"
        "- 'MP3' ile ses, 'Video' ile görüntü alırsın.\n"
        "- Link at, gerisini bana bırak! 50 MB’tan büyük dosyalarda üzülürüm ama yine de çalışırım. 😅\n"
        "- 50 MB üzeri içerikleri indirebilmek için PREMIUM hesabınız olmalı üzgünüm, TELEGRAM KURALI \n"
        "Sorun mu var? Bana söyle, çözeriz!",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
    )
    return FORMAT_SELECTION

async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text(
        "Tamam, MP3 indirelim! Bana bir link at, hemen başlayayım.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
    )
    return URL_WAITING

async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'video'
    await update.message.reply_text(
        "Video dedin, süper! Linkini at, indirelim.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
    )
    return URL_WAITING

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.effective_chat.id
    selected_format = context.user_data.get('format', 'mp3')

    # Durum göstergesi
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Linkini aldım, indiriyorum... ⏳"
    )

    if selected_format == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'cookiefile': None,
        }
    else:  # video
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'cookiefile': None,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            time.sleep(1)  # Basit ilerleme hissi
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text="Hala indiriyorum, biraz sabır... ⏳"
            )
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)
            if selected_format == 'mp3':
                file_name = file_name.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            else:
                file_name = file_name.rsplit('.', 1)[0] + '.mp4'

        if not os.path.exists(file_name):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_name}")

        # Dosya boyutunu kontrol et
        file_size_mb = os.path.getsize(file_name) / (1024 * 1024)
        if file_size_mb > 50:
            await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Oha, bu dosya {file_size_mb:.2f} MB! Telegram 50 MB’a kadar alıyor, daha kısa bir şey seçelim mi? 😅",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
            )
            os.remove(file_name)
            return FORMAT_SELECTION

        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        with open(file_name, 'rb') as media:
            if selected_format == 'mp3':
                await context.bot.send_audio(chat_id=chat_id, audio=media, title=info['title'])
            else:
                await context.bot.send_video(chat_id=chat_id, video=media)

        await context.bot.send_message(
            chat_id=chat_id,
            text="İndirme tamamlandı, işte dosyan! 🎉 Başka neyi indireyim?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        )
        os.remove(file_name)

    except Exception as e:
        logger.error(f"Hata detayları: {str(e)}")
        await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Ups, bir şeyler ters gitti: {str(e)}. Link mi yanlış, yoksa ben mi şaşırdım? 😅",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="Neyse, pes etmeyelim! Başka bir şey deneyelim mi?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
        )

    return FORMAT_SELECTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Tamam, vazgeçtik o zaman. 😊 Yeniden başlamak istersen 'Start' butonuna bas!",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False, resize_keyboard=True)
    )
    return ConversationHandler.END

def main():
    token = os.getenv('TOKEN')
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FORMAT_SELECTION: [
                CommandHandler('mp3', mp3_command),
                CommandHandler('video', video_command),
                CommandHandler('yardim', yardim),
                CommandHandler('start', start),
                MessageHandler(filters.Regex('^(MP3|Video|Yardım|Start)$'), lambda u, c: mp3_command(u, c) if u.message.text == 'MP3' else video_command(u, c) if u.message.text == 'Video' else yardim(u, c) if u.message.text == 'Yardım' else start(u, c)),
            ],
            URL_WAITING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(filters.Regex('^Cancel$'), cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('yardim', yardim))
    application.run_polling()

if __name__ == '__main__':
    main()