# ==UserScript==
# name: Telegram Multi Downloader Bot
# namespace: https://github.com/yourusername/telegram-downloader-bot
# version: 1.0.0
# description: TikTok, Youtube, Instagram downloader bot for Telegram
# ==/UserScript==

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs
import re
import requests
from flask import Flask, request, jsonify
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ===== 1. تنظیمات و ثابت‌ها =====
TOKEN = '6760597309:AAGVt108eMSVCXjSeMePfcf1L5paCzGl6PY'
ADMIN_GROUP_ID = -5478649286
CHANNEL_ID = '@my_channel'
BOT_NAME = 'دانلودر شوگوت'

# تنظیمات Railway
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://your-app-name.railway.app/webhook')

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== 2. کتابخانه‌های دانلود =====
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not installed. Install with: pip install yt-dlp")

try:
    from instaloader import Instaloader, Post
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False
    logger.warning("instaloader not installed. Install with: pip install instaloader")

try:
    from TikTokApi import TikTokApi
    TIKTOK_API_AVAILABLE = True
except ImportError:
    TIKTOK_API_AVAILABLE = False
    logger.warning("TikTokApi not installed. Install with: pip install TikTokApi")

# ===== 3. کلاس حافظه ساده =====
class SimpleMemory:
    def __init__(self):
        self.data = {}
    
    def set(self, key, value):
        self.data[key] = value
    
    def get(self, key):
        return self.data.get(key)
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
    
    def has(self, key):
        return key in self.data

memory = SimpleMemory()

# ===== 4. توابع کمکی =====
def get_tehran_time():
    from datetime import timedelta, timezone
    tehran_offset = timedelta(hours=3, minutes=30)
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=0))) + tehran_offset

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

# ===== 5. توابع دانلود =====
async def download_tiktok(url):
    """دانلود ویدیو از تیک تاک"""
    try:
        if TIKTOK_API_AVAILABLE:
            # استفاده از TikTokApi
            api = TikTokApi()
            video_data = api.video(url)
            video_url = video_data['video']['downloadAddr']
            if video_url:
                logger.info(f"✅ TikTok downloaded with TikTokApi")
                return video_url
        
        # روش جایگزین: استفاده از yt-dlp برای تیک تاک
        if YT_DLP_AVAILABLE:
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'url' in info:
                    logger.info(f"✅ TikTok downloaded with yt-dlp")
                    return info['url']
        
        # روش سوم: استفاده از API عمومی
        try:
            response = requests.get(f'https://www.tikwm.com/api/?url={url}')
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                video_url = data['data'].get('play') or data['data'].get('wmplay') or data['data'].get('hdplay')
                if video_url:
                    logger.info(f"✅ TikTok downloaded with tikwm")
                    return video_url
        except:
            pass
        
        raise Exception('ویدیو پیدا نشد')
        
    except Exception as e:
        logger.error(f"TikTok download error: {e}")
        raise Exception(f"خطا در دانلود تیک تاک: {str(e)}")

async def download_youtube(url):
    """دانلود ویدیو از یوتیوب"""
    try:
        if not YT_DLP_AVAILABLE:
            raise Exception('yt-dlp نصب نیست')
        
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'url' in info:
                logger.info(f"✅ Youtube downloaded with yt-dlp")
                return info['url']
            elif info and 'formats' in info:
                # انتخاب بهترین کیفیت
                video_url = info['formats'][0]['url']
                logger.info(f"✅ Youtube downloaded with yt-dlp (format)")
                return video_url
        
        raise Exception('ویدیو پیدا نشد')
        
    except Exception as e:
        logger.error(f"Youtube download error: {e}")
        raise Exception(f"خطا در دانلود یوتیوب: {str(e)}")

async def download_instagram(url):
    """دانلود ویدیو از اینستاگرام (پست و ریلز)"""
    try:
        insta_id = extract_instagram_id(url)
        if not insta_id:
            raise Exception('لینک اینستاگرام معتبر نیست')
        
        # روش اول: استفاده از instaloader
        if INSTALOADER_AVAILABLE:
            try:
                loader = Instaloader()
                post = Post.from_shortcode(loader.context, insta_id)
                if post.is_video:
                    video_url = post.video_url
                    if video_url:
                        logger.info(f"✅ Instagram downloaded with instaloader")
                        return video_url
            except Exception as e:
                logger.warning(f"Instaloader error: {e}")
        
        # روش دوم: استفاده از yt-dlp
        if YT_DLP_AVAILABLE:
            try:
                ydl_opts = {
                    'format': 'best[ext=mp4]',
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info and 'url' in info:
                        logger.info(f"✅ Instagram downloaded with yt-dlp")
                        return info['url']
            except Exception as e:
                logger.warning(f"yt-dlp for Instagram error: {e}")
        
        # روش سوم: استفاده از API رسمی اینستاگرام
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(f'https://www.instagram.com/p/{insta_id}/?__a=1&__d=dis', headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('graphql', {}).get('shortcode_media', {}).get('video_url'):
                    video_url = data['graphql']['shortcode_media']['video_url']
                    logger.info(f"✅ Instagram downloaded with API")
                    return video_url
        except Exception as e:
            logger.warning(f"Instagram API error: {e}")
        
        raise Exception('ویدیو پیدا نشد')
        
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
        raise Exception(f"خطا در دانلود اینستاگرام: {str(e)}")

# ===== 6. توابع Telegram API =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /start"""
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
            InlineKeyboardButton("🎵 TikTok Downloader", callback_data="download_TikTok"),
            InlineKeyboardButton("🎬 Youtube Downloader", callback_data="download_Youtube"),
        ],
        [
            InlineKeyboardButton("📸 Instagram Downloader", callback_data="download_Instagram"),
            InlineKeyboardButton("📢 کانال", callback_data="channel"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دکمه‌های کیبورد"""
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
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    if data.startswith('download_'):
        platform = data.replace('download_', '')
        memory.set(chat_id, {'platform': platform, 'step': 'waiting_for_link'})
        
        persian_date = format_persian_date(get_tehran_time())
        message = f"""📥 دانلود از <b>{platform}</b>

🔗 لطفاً لینک ویدیو را ارسال کنید:

مثال:
{platform == 'TikTok' and 'https://www.tiktok.com/@user/video/123456789' or 
 platform == 'Youtube' and 'https://www.youtube.com/watch?v=VIDEO_ID' or 
 'https://www.instagram.com/reel/VIDEO_ID/'}

⏰ زمان تهران: {persian_date}"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر پیام‌های متنی"""
    chat_id = update.effective_chat.id
    text = update.message.text
    
    state = memory.get(chat_id)
    if not state or state.get('step') != 'waiting_for_link':
        keyboard = [
            [
                InlineKeyboardButton("🎵 TikTok Downloader", callback_data="download_TikTok"),
                InlineKeyboardButton("🎬 Youtube Downloader", callback_data="download_Youtube"),
            ],
            [
                InlineKeyboardButton("📸 Instagram Downloader", callback_data="download_Instagram"),
                InlineKeyboardButton("📢 کانال", callback_data="channel"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            '⚠️ لطفاً ابتدا از منوی اصلی یک پلتفرم انتخاب کنید.',
            parse_mode='HTML',
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
        await update.message.reply_text(
            '❌ لینک وارد شده معتبر نیست. لطفاً یک لینک معتبر از پلتفرم مورد نظر ارسال کنید.'
        )
        return
    
    # پردازش دانلود
    state['link'] = text
    state['step'] = 'processing'
    memory.set(chat_id, state)
    
    processing_msg = await update.message.reply_text(f'⏳ در حال دانلود ویدیو از <b>{state["platform"]}</b>...', parse_mode='HTML')
    
    try:
        # دانلود ویدیو
        video_url = None
        if state['platform'] == 'TikTok':
            video_url = await download_tiktok(text)
        elif state['platform'] == 'Youtube':
            video_url = await download_youtube(text)
        elif state['platform'] == 'Instagram':
            video_url = await download_instagram(text)
        
        if not video_url:
            raise Exception('ویدیو پیدا نشد')
        
        # ارسال ویدیو
        persian_date = format_persian_date(get_tehran_time())
        caption = f"""✅ دانلود با موفقیت انجام شد!

🎯 پلتفرم: <b>{state['platform']}</b>
🔗 لینک: {text}
📅 تاریخ و ساعت: {persian_date}"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
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
        
        # حذف پیام پردازش
        await processing_msg.delete()
        
        # پاک کردن حافظه
        memory.delete(chat_id)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        error_message = f"❌ خطا در دانلود ویدیو. {str(e)}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(error_message, parse_mode='HTML', reply_markup=reply_markup)
        memory.delete(chat_id)

# ===== 7. راه‌اندازی Flask برای Webhook =====
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
    """دریافت درخواست‌های تلگرام"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    """سلامت سنجی برای Railway"""
    return jsonify({'status': 'ok', 'time': format_persian_date(get_tehran_time())})

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    """تنظیم Webhook"""
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== 8. راه‌اندازی اصلی =====
if __name__ == '__main__':
    # ایجاد اپلیکیشن تلگرام
    application = Application.builder().token(TOKEN).build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تنظیم Webhook
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        )
        logger.info(f"Webhook set: {response.json()}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
    
    # راه‌اندازی Flask
    app.run(host='0.0.0.0', port=PORT)
