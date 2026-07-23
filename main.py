# main.py
# Telegram Multi Downloader Bot - نسخه نهایی با Webhook

import os
import re
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify

# ============================================
# تنظیمات
# ============================================

TOKEN = '6760597309:AAGVt108eMSVCXjSeMePfcf1L5paCzGl6PY'
ADMIN_GROUP_ID = -5478649286
CHANNEL_ID = '@my_channel'
BOT_NAME = 'دانلودر شوگوت'

PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

# ============================================
# لاگ
# ============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# حافظه ساده
# ============================================

memory = {}

def set_memory(chat_id, data):
    memory[str(chat_id)] = data

def get_memory(chat_id):
    return memory.get(str(chat_id))

def delete_memory(chat_id):
    key = str(chat_id)
    if key in memory:
        del memory[key]

# ============================================
# توابع کمکی
# ============================================

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

# ============================================
# توابع دانلود
# ============================================

def download_tiktok(url):
    try:
        response = requests.get(
            f'https://www.tikwm.com/api/?url={url}',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        data = response.json()
        if data.get('code') == 0 and data.get('data'):
            video_url = data['data'].get('play') or data['data'].get('wmplay')
            if video_url:
                return video_url
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"TikTok error: {e}")
        raise Exception(f"خطا در دانلود تیک تاک")

def download_youtube(url):
    try:
        youtube_id = extract_youtube_id(url)
        if not youtube_id:
            raise Exception('لینک یوتیوب معتبر نیست')
        
        response = requests.get(
            f'https://api.vevioz.com/api/button/mp4/{youtube_id}',
            timeout=20,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
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
        raise Exception(f"خطا در دانلود یوتیوب")

def download_instagram(url):
    try:
        insta_id = extract_instagram_id(url)
        if not insta_id:
            raise Exception('لینک اینستاگرام معتبر نیست')
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(
            f'https://www.instagram.com/p/{insta_id}/?__a=1&__d=dis',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            video_url = data.get('graphql', {}).get('shortcode_media', {}).get('video_url')
            if video_url:
                return video_url
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"Instagram error: {e}")
        raise Exception(f"خطا در دانلود اینستاگرام")

# ============================================
# توابع ارسال به تلگرام
# ============================================

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        return None

def send_video(chat_id, video_url, caption, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
    data = {
        'chat_id': chat_id,
        'video': video_url,
        'caption': caption,
        'parse_mode': 'HTML',
        'supports_streaming': True
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, data=data, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Send video error: {e}")
        return None

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {'callback_query_id': callback_id}
    
    try:
        response = requests.post(url, data=data, timeout=5)
        return response.json()
    except:
        return None

def delete_message(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    data = {'chat_id': chat_id, 'message_id': message_id}
    
    try:
        response = requests.post(url, data=data, timeout=5)
        return response.json()
    except:
        return None

# ============================================
# کیبوردها
# ============================================

def get_keyboard():
    return {
        'inline_keyboard': [
            [
                {'text': '🎵 TikTok', 'callback_data': 'download_TikTok'},
                {'text': '🎬 Youtube', 'callback_data': 'download_Youtube'},
            ],
            [
                {'text': '📸 Instagram', 'callback_data': 'download_Instagram'},
                {'text': '📢 کانال', 'callback_data': 'channel'},
            ],
        ]
    }

def get_back_keyboard():
    return {
        'inline_keyboard': [
            [{'text': '🔙 بازگشت', 'callback_data': 'main_menu'}]
        ]
    }

# ============================================
# هندلرها
# ============================================

def handle_start(chat_id):
    persian_date = format_persian_date(get_tehran_time())
    
    message = f"""👋 به <b>{BOT_NAME}</b> خوش آمدید!

🎯 این ربات به شما کمک می‌کند تا ویدیوهای مورد نظر خود را دانلود کنید:

🎵 TikTok
🎬 Youtube
📸 Instagram (پست و ریلز)

📌 از منوی زیر یکی را انتخاب کنید.
⏰ {persian_date}"""
    
    send_message(chat_id, message, get_keyboard())

def handle_callback(data, chat_id, message_id, callback_id):
    answer_callback(callback_id)
    
    if data == 'main_menu':
        handle_start(chat_id)
        return
    
    if data == 'channel':
        persian_date = format_persian_date(get_tehran_time())
        message = f"""📢 <b>کانال رسمی {BOT_NAME}</b>

🔗 {CHANNEL_ID}

📱 منتظر شما هستیم! 🎬
⏰ {persian_date}"""
        
        edit_message(chat_id, message_id, message, get_back_keyboard())
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

🔗 لینک ویدیو را ارسال کنید:

مثال:
{examples.get(platform, '')}

⏰ {persian_date}"""
        
        edit_message(chat_id, message_id, message, get_back_keyboard())

def handle_message(chat_id, text):
    state = get_memory(chat_id)
    
    if not state or state.get('step') != 'waiting_for_link':
        send_message(chat_id, '⚠️ ابتدا از منو یک پلتفرم انتخاب کنید.', get_keyboard())
        return
    
    platform = state['platform'].lower()
    url_patterns = {
        'tiktok': r'(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/.+',
        'youtube': r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+',
        'instagram': r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/.+',
    }
    
    if not re.match(url_patterns[platform], text, re.I):
        send_message(chat_id, '❌ لینک معتبر نیست. دوباره تلاش کنید.')
        return
    
    state['link'] = text
    state['step'] = 'processing'
    set_memory(chat_id, state)
    
    msg = send_message(chat_id, f'⏳ در حال دانلود از <b>{state["platform"]}</b>...', None)
    processing_msg_id = msg['result']['message_id'] if msg and msg.get('ok') else None
    
    try:
        video_url = None
        if state['platform'] == 'TikTok':
            video_url = download_tiktok(text)
        elif state['platform'] == 'Youtube':
            video_url = download_youtube(text)
        elif state['platform'] == 'Instagram':
            video_url = download_instagram(text)
        
        if not video_url:
            raise Exception('ویدیو پیدا نشد')
        
        persian_date = format_persian_date(get_tehran_time())
        caption = f"""✅ دانلود موفق!

🎯 {state['platform']}
🔗 {text}
📅 {persian_date}"""
        
        send_video(chat_id, video_url, caption, get_back_keyboard())
        
        admin_msg = f"""📤 دانلود جدید
🎯 {state['platform']}
🔗 {text}
📅 {persian_date}"""
        send_message(ADMIN_GROUP_ID, admin_msg)
        
        if processing_msg_id:
            delete_message(chat_id, processing_msg_id)
        
        delete_memory(chat_id)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        send_message(chat_id, f"❌ خطا: {str(e)}", get_back_keyboard())
        delete_memory(chat_id)

# ============================================
# Flask App
# ============================================

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if 'message' in data:
            msg = data['message']
            chat_id = msg['chat']['id']
            
            if 'text' in msg:
                text = msg['text']
                if text == '/start':
                    handle_start(chat_id)
                else:
                    handle_message(chat_id, text)
        
        elif 'callback_query' in data:
            cb = data['callback_query']
            chat_id = cb['message']['chat']['id']
            message_id = cb['message']['message_id']
            callback_id = cb['id']
            data_cb = cb['data']
            
            handle_callback(data_cb, chat_id, message_id, callback_id)
        
        return 'OK', 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'time': format_persian_date(get_tehran_time())
    })

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    try:
        if not WEBHOOK_URL:
            return jsonify({'error': 'WEBHOOK_URL not set in environment variables'}), 400
        
        webhook_url = f"{WEBHOOK_URL}/webhook"
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'name': BOT_NAME,
        'status': 'running',
        'time': format_persian_date(get_tehran_time()),
        'webhook_url': f"{WEBHOOK_URL}/webhook" if WEBHOOK_URL else 'Not set'
    })

# ============================================
# اجرا
# ============================================

if __name__ == '__main__':
    if WEBHOOK_URL:
        try:
            webhook_url = f"{WEBHOOK_URL}/webhook"
            response = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
            )
            logger.info(f"✅ Webhook set: {response.json()}")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
    else:
        logger.warning("⚠️ WEBHOOK_URL not set. Set it in Railway environment variables.")
    
    app.run(host='0.0.0.0', port=PORT)
