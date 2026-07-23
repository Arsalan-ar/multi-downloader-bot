# main.py
# Telegram Multi Downloader Bot - نسخه Railway

import os
import json
import logging
import re
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== تنظیمات =====
TOKEN = '6760597309:AAGVt108eMSVCXjSeMePfcf1L5paCzGl6PY'
ADMIN_GROUP_ID = -5478649286
CHANNEL_ID = '@my_channel'
BOT_NAME = 'دانلودر شوگوت'

PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://your-app-name.railway.app')

# ===== لاگ =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== حافظه ساده =====
memory = {}

def set_memory(key, value):
    memory[key] = value

def get_memory(key):
    return memory.get(key)

def delete_memory(key):
    if key in memory:
        del memory[key]

# ===== توابع کمکی =====
def get_tehran_time():
    tehran_offset = timedelta(hours=3, minutes=30)
    return datetime.now(timezone.utc).astimezone() + tehran_offset

def format_persian_date(date):
    persian_months = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    return date.strftime(f'%d {persian_months[date.month-1]} %Y، ساعت %H:%M:%S')

def extract_youtube_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)',
        r'youtube\.com\/embed\/([^\/]+)',
        r'youtube\.com\/v\/([^\/]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_instagram_id(url):
    patterns = [
        r'instagram\.com\/(?:p|reel|tv)\/([^\/?]+)',
        r'instagram\.com\/p\/([^\/]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# ===== توابع دانلود =====
def download_tiktok(url):
    try:
        # روش اول: tikwm
        response = requests.get(f'https://www.tikwm.com/api/?url={url}', timeout=10)
        data = response.json()
        if data.get('code') == 0 and data.get('data'):
            video_url = data['data'].get('play') or data['data'].get('wmplay') or data['data'].get('hdplay')
            if video_url:
                return video_url
        
        # روش دوم: tikmate
        response = requests.get(f'https://tikmate.online/api/j/convert?url={url}', timeout=10)
        data = response.json()
        if data.get('video_url'):
            return data['video_url']
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"TikTok error: {e}")
        raise Exception(f"خطا در دانلود تیک تاک: {str(e)}")

def download_youtube(url):
    try:
        # استفاده از y2mate
        youtube_id = extract_youtube_id(url)
        if not youtube_id:
            raise Exception('لینک یوتیوب معتبر نیست')
        
        # روش اول: y2mate
        response = requests.post(
            'https://www.y2mate.com/mates/en68/analyze/ajax',
            data={'url': f'https://www.youtube.com/watch?v={youtube_id}', 'q': '360'},
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=15
        )
        if response.status_code == 200:
            text = response.text
            match = re.search(r'https?://[^"\'s]+\.mp4', text)
            if match:
                return match.group(0)
        
        # روش دوم: vevioz
        response = requests.get(f'https://api.vevioz.com/api/button/mp4/{youtube_id}', timeout=15)
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('download'):
                    return data['download']
            except:
                match = re.search(r'https?://[^"\'s]+\.mp4', response.text)
                if match:
                    return match.group(0)
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"Youtube error: {e}")
        raise Exception(f"خطا در دانلود یوتیوب: {str(e)}")

def download_instagram(url):
    try:
        insta_id = extract_instagram_id(url)
        if not insta_id:
            raise Exception('لینک اینستاگرام معتبر نیست')
        
        # روش اول: API رسمی
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(f'https://www.instagram.com/p/{insta_id}/?__a=1&__d=dis', headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('graphql', {}).get('shortcode_media', {}).get('video_url'):
                return data['graphql']['shortcode_media']['video_url']
        
        # روش دوم: oembed
        response = requests.get(f'https://api.instagram.com/oembed?url={url}', timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('thumbnail_url'):
                return data['thumbnail_url']
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"Instagram error: {e}")
        raise Exception(f"خطا در دانلود اینستاگرام: {str(e)}")

# ===== هندلرهای تلگرام =====
async def start(update, context):
    chat_id = update.effective_chat.id
    persian_date = format_persian_date(get_tehran_time())
    
    message = f"""👋 به <b>{BOT_NAME}</b> خوش آمدید!

🎯 این ربات به شما کمک می‌کند تا ویدیوهای مورد نظر خود را از پلتفرم‌های زیر دانلود کنید:

🎵 TikTok
🎬 Youtube
📸 Instagram (پست و ریلز)

📌 لطفاً از منوی زیر یکی از گزینه‌ها را انتخاب کنید.
⏰ زمان تهران: {persian_date}"""
    
    keyboard = [
        [
            InlineKeyboardButton("🎵 TikTok", callback_data="download_TikTok"),
            InlineKeyboardButton("🎬 Youtube", callback_data="download_Youtube"),
        ],
        [
            InlineKeyboardButton("📸 Instagram", callback_data="download_Instagram"),
            InlineKeyboardButton("📢 کانال", callback_data="channel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    message_id = query.message.message_id
    data = query.data
    
    if data == 'main_menu':
        await start(update, context)
        return
    
    if data == 'channel':
        persian_date = format_persian_date(get_tehran_time())
        message = f"""📢 <b>کانال رسمی {BOT_NAME}</b>

برای دسترسی به آخرین ویدیوها و محتوای جدید، به کانال ما بپیوندید:

🔗 {CHANNEL_ID}

📱 منتظر شما هستیم! 🎬
⏰ {persian_date}"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    if data.startswith('download_'):
        platform = data.replace('download_', '')
        set_memory(chat_id, {'platform': platform, 'step': 'waiting_for_link'})
        
        persian_date = format_persian_date(get_tehran_time())
        examples = {
            'TikTok': 'https://www.tiktok.com/@user/video/123456789',
            'Youtube': 'https://www.youtube.com/watch?v=VIDEO_ID',
            'Instagram': 'https://www.instagram.com/reel/VIDEO_ID/'
        }
        
        message = f"""📥 دانلود از <b>{platform}</b>

🔗 لطفاً لینک ویدیو را ارسال کنید:

مثال:
{examples.get(platform, '')}

⏰ زمان تهران: {persian_date}"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_message(update, context):
    chat_id = update.effective_chat.id
    text = update.message.text
    
    state = get_memory(chat_id)
    if not state or state.get('step') != 'waiting_for_link':
        keyboard = [
            [
                InlineKeyboardButton("🎵 TikTok", callback_data="download_TikTok"),
                InlineKeyboardButton("🎬 Youtube", callback_data="download_Youtube"),
            ],
            [
                InlineKeyboardButton("📸 Instagram", callback_data="download_Instagram"),
                InlineKeyboardButton("📢 کانال", callback_data="channel"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            '⚠️ لطفاً ابتدا از منوی اصلی یک پلتفرم انتخاب کنید.',
            reply_markup=reply_markup
        )
        return
    
    # اعتبارسنجی لینک
    platform = state['platform'].lower()
    url_patterns = {
        'tiktok': r'(https?:\/\/)?(www\.)?(tiktok\.com|vm\.tiktok\.com)\/.+',
        'youtube': r'(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+',
        'instagram': r'(https?:\/\/)?(www\.)?(instagram\.com|instagr\.am)\/.+',
    }
    
    if not re.match(url_patterns[platform], text, re.I):
        await update.message.reply_text('❌ لینک وارد شده معتبر نیست. لطفاً دوباره تلاش کنید.')
        return
    
    state['link'] = text
    state['step'] = 'processing'
    set_memory(chat_id, state)
    
    processing_msg = await update.message.reply_text(f'⏳ در حال دانلود ویدیو از <b>{state["platform"]}</b>...', parse_mode='HTML')
    
    try:
        # دانلود ویدیو
        video_url = None
        if state['platform'] == 'TikTok':
            video_url = download_tiktok(text)
        elif state['platform'] == 'Youtube':
            video_url = download_youtube(text)
        elif state['platform'] == 'Instagram':
            video_url = download_instagram(text)
        
        if not video_url:
            raise Exception('ویدیو پیدا نشد')
        
        # ارسال ویدیو
        persian_date = format_persian_date(get_tehran_time())
        caption = f"""✅ دانلود با موفقیت انجام شد!

🎯 پلتفرم: <b>{state['platform']}</b>
🔗 لینک: {text}
📅 تاریخ و ساعت: {persian_date}"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_video(
            video_url,
            caption=caption,
            parse_mode='HTML',
            reply_markup=reply_markup,
            supports_streaming=True
        )
        
        # ارسال به گروه ادمین
        admin_message = f"""📤 دانلود انجام شد
🎯 پلتفرم: {state['platform']}
🔗 لینک: {text}
📅 تاریخ: {persian_date}"""
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_message)
        
        await processing_msg.delete()
        delete_memory(chat_id)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        error_message = f"❌ خطا در دانلود ویدیو. {str(e)}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(error_message, reply_markup=reply_markup)
        delete_memory(chat_id)

# ===== Flask App =====
app = Flask(__name__)

# ایجاد اپلیکیشن تلگرام
application = Application.builder().token(TOKEN).build()

# ثبت هندلرها
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(button_callback))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.process_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': format_persian_date(get_tehran_time())})

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== اجرا =====
if __name__ == '__main__':
    # تنظیم Webhook
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        )
        logger.info(f"Webhook set: {response.json()}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
    
    app.run(host='0.0.0.0', port=PORT)
