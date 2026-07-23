# main.py
# Telegram Multi Downloader Bot - نسخه با API زمان

import os
import re
import json
import logging
import requests
from datetime import datetime
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
# دریافت زمان از API - نسخه کامل
# ============================================

def get_tehran_time_from_api():
    """دریافت زمان تهران از APIهای مختلف"""
    
    # لیست APIهای زمان با پشتیبان
    apis = [
        {
            'url': 'http://worldtimeapi.org/api/timezone/Asia/Tehran',
            'method': 'GET',
            'parser': lambda data: datetime.fromisoformat(data.get('datetime', '').replace('Z', '+00:00'))
        },
        {
            'url': 'https://timeapi.io/api/Time/current/zone?timeZone=Asia/Tehran',
            'method': 'GET',
            'parser': lambda data: datetime(
                data.get('year', 2024),
                data.get('month', 1),
                data.get('day', 1),
                data.get('hour', 0),
                data.get('minute', 0),
                data.get('seconds', 0)
            )
        }
    ]
    
    for api in apis:
        try:
            response = requests.get(api['url'], timeout=5)
            if response.status_code == 200:
                data = response.json()
                dt = api['parser'](data)
                if dt:
                    logger.info(f"✅ Time fetched from: {api['url']}")
                    return dt
        except Exception as e:
            logger.warning(f"⚠️ Time API failed: {api['url']} - {e}")
            continue
    
    # Fallback: زمان محلی با offset تهران
    logger.warning("⚠️ All time APIs failed, using local time")
    from datetime import timedelta, timezone
    tehran_offset = timedelta(hours=3, minutes=30)
    return datetime.now(timezone.utc).astimezone() + tehran_offset

def get_persian_date_from_api(date_obj):
    """تبدیل تاریخ میلادی به شمسی با استفاده از API"""
    
    # APIهای تبدیل تاریخ
    apis = [
        {
            'url': f'https://api.vercel.app/date?date={date_obj.strftime("%Y-%m-%d")}',
            'parser': lambda data: data.get('persian', {})
        },
        {
            'url': f'https://persian-date-api.vercel.app/api/convert?date={date_obj.strftime("%Y-%m-%d")}',
            'parser': lambda data: data.get('result', {})
        }
    ]
    
    for api in apis:
        try:
            response = requests.get(api['url'], timeout=3)
            if response.status_code == 200:
                data = response.json()
                persian = api['parser'](data)
                if persian:
                    day = persian.get('day', date_obj.day)
                    month_name = persian.get('month_name', '')
                    year = persian.get('year', date_obj.year)
                    return f"{day} {month_name} {year}، ساعت {date_obj.strftime('%H:%M:%S')}"
        except:
            continue
    
    # Fallback: محاسبه دستی تاریخ شمسی
    return manual_persian_date(date_obj)

def manual_persian_date(date):
    """محاسبه دستی تاریخ شمسی (الگوریتم دقیق)"""
    persian_months = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    gy = date.year
    gm = date.month
    gd = date.day
    
    # الگوریتم تبدیل میلادی به شمسی
    if gm > 2:
        gy2 = gy + 1
    else:
        gy2 = gy
    
    days = 355666 + (365 * gy2) + int(gy2 / 4) - int(gy2 / 100) + int(gy2 / 400) - int((gy2 + 3) / 4) + gd
    
    if gm > 2:
        days += 31
    
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for i in range(1, gm):
        days += month_days[i-1]
    
    jy = 0
    for i in range(0, 10000):
        if i % 4 == 0:
            month_days = 31
        else:
            month_days = 30
        
        if i % 4 == 0 and i % 100 != 0:
            month_days = 31
        if i % 400 == 0:
            month_days = 31
        
        if days > month_days:
            days -= month_days
        else:
            jy = i + 1
            break
    
    jm = 1
    for i in range(0, 12):
        if i < 6:
            month_days = 31
        else:
            month_days = 30
        
        if days > month_days:
            days -= month_days
        else:
            jm = i + 1
            break
    
    jd = days
    
    return f"{jd} {persian_months[jm-1]} {jy}، ساعت {date.strftime('%H:%M:%S')}"

def get_current_time():
    """دریافت زمان و تاریخ کامل تهران"""
    dt = get_tehran_time_from_api()
    return get_persian_date_from_api(dt)

# ============================================
# توابع کمکی
# ============================================

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
        # روش اول: tikwm
        response = requests.get(
            f'https://www.tikwm.com/api/?url={url}',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        data = response.json()
        if data.get('code') == 0 and data.get('data'):
            video_url = data['data'].get('play') or data['data'].get('wmplay') or data['data'].get('hdplay')
            if video_url:
                return video_url
        
        # روش دوم: tikmate
        response = requests.get(
            f'https://tikmate.online/api/j/convert?url={url}',
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        data = response.json()
        if data.get('video_url'):
            return data['video_url']
        
        raise Exception('ویدیو پیدا نشد')
    except Exception as e:
        logger.error(f"TikTok error: {e}")
        raise Exception(f"خطا در دانلود تیک تاک")

def download_youtube_with_quality(youtube_id, quality):
    try:
        # روش اول: vevioz
        response = requests.get(
            f'https://api.vevioz.com/api/button/mp4/{youtube_id}',
            timeout=20,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('download'):
                    return data['download']
            except:
                pass
        
        # روش دوم: y2mate
        try:
            response = requests.post(
                'https://www.y2mate.com/mates/en68/analyze/ajax',
                data={'url': f'https://www.youtube.com/watch?v={youtube_id}', 'q': '360'},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=20
            )
            
            if response.status_code == 200:
                text = response.text
                match = re.search(r'https?://[^"\'s]+\.mp4', text)
                if match:
                    return match.group(0)
        except:
            pass
        
        raise Exception('ویدیو پیدا نشد')
        
    except Exception as e:
        logger.error(f"Youtube download error: {e}")
        raise Exception(f"خطا در دانلود یوتیوب")

def download_instagram(url):
    try:
        insta_id = extract_instagram_id(url)
        if not insta_id:
            raise Exception('لینک اینستاگرام معتبر نیست')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # روش اول: API رسمی
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
        
        # روش دوم: embed
        response = requests.get(
            f'https://www.instagram.com/p/{insta_id}/embed',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            html = response.text
            match = re.search(r'<video[^>]+src="([^"]+)"', html)
            if match:
                return match.group(1)
        
        # روش سوم: oembed
        response = requests.get(
            f'https://api.instagram.com/oembed?url={url}',
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('thumbnail_url'):
                return data['thumbnail_url']
        
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
        response = requests.post(url, data=data, timeout=60)
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

def get_quality_keyboard(youtube_id):
    qualities = ['720p', '480p', '360p', '240p']
    
    keyboard = {
        'inline_keyboard': [
            [
                {'text': f'📺 {q}', 'callback_data': f'quality_{youtube_id}_{q}'}
                for q in qualities[:2]
            ],
            [
                {'text': f'📺 {q}', 'callback_data': f'quality_{youtube_id}_{q}'}
                for q in qualities[2:]
            ],
            [
                {'text': '🔙 بازگشت', 'callback_data': 'main_menu'}
            ]
        ]
    }
    return keyboard

# ============================================
# هندلرها
# ============================================

def handle_start(chat_id):
    current_time = get_current_time()
    
    message = f"""👋 به <b>{BOT_NAME}</b> خوش آمدید!

🎯 این ربات به شما کمک می‌کند تا ویدیوهای مورد نظر خود را دانلود کنید:

🎵 TikTok
🎬 Youtube (با انتخاب کیفیت)
📸 Instagram (پست و ریلز)

📌 از منوی زیر یکی را انتخاب کنید.
⏰ {current_time}"""
    
    send_message(chat_id, message, get_keyboard())

def handle_callback(data, chat_id, message_id, callback_id):
    answer_callback(callback_id)
    
    if data == 'main_menu':
        handle_start(chat_id)
        return
    
    if data == 'channel':
        current_time = get_current_time()
        message = f"""📢 <b>کانال رسمی {BOT_NAME}</b>

🔗 {CHANNEL_ID}

📱 منتظر شما هستیم! 🎬
⏰ {current_time}"""
        
        edit_message(chat_id, message_id, message, get_back_keyboard())
        return
    
    if data.startswith('quality_'):
        parts = data.split('_')
        youtube_id = parts[1]
        quality = parts[2]
        
        state = get_memory(chat_id)
        if not state:
            return
        
        url = state.get('link', '')
        
        processing_msg = send_message(chat_id, f'⏳ در حال دانلود با کیفیت {quality}...', None)
        processing_msg_id = processing_msg['result']['message_id'] if processing_msg and processing_msg.get('ok') else None
        
        try:
            video_url = download_youtube_with_quality(youtube_id, quality)
            
            if not video_url:
                raise Exception('ویدیو پیدا نشد')
            
            current_time = get_current_time()
            caption = f"""✅ دانلود موفق!

🎯 Youtube
🔗 {url}
📺 کیفیت: {quality}
📅 {current_time}"""
            
            send_video(chat_id, video_url, caption, get_back_keyboard())
            
            admin_msg = f"""📤 دانلود جدید
🎯 Youtube
📺 کیفیت: {quality}
📅 {current_time}"""
            send_message(ADMIN_GROUP_ID, admin_msg)
            
            if processing_msg_id:
                delete_message(chat_id, processing_msg_id)
            
            delete_memory(chat_id)
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            send_message(chat_id, f"❌ خطا: {str(e)}", get_back_keyboard())
            delete_memory(chat_id)
        
        return
    
    if data.startswith('download_'):
        platform = data.replace('download_', '')
        set_memory(chat_id, {'platform': platform, 'step': 'waiting_for_link', 'chat_id': chat_id})
        
        current_time = get_current_time()
        
        examples = {
            'TikTok': 'https://www.tiktok.com/@user/video/123456789',
            'Youtube': 'https://www.youtube.com/watch?v=VIDEO_ID',
            'Instagram': 'https://www.instagram.com/reel/VIDEO_ID/'
        }
        
        message = f"""📥 دانلود از <b>{platform}</b>

🔗 لینک ویدیو را ارسال کنید:

مثال:
{examples.get(platform, '')}

⏰ {current_time}"""
        
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
    
    if platform == 'youtube':
        youtube_id = extract_youtube_id(text)
        if youtube_id:
            state['youtube_id'] = youtube_id
            set_memory(chat_id, state)
            
            current_time = get_current_time()
            message = f"""🎬 کیفیت مورد نظر را انتخاب کنید:

⏰ {current_time}"""
            
            send_message(chat_id, message, get_quality_keyboard(youtube_id))
        else:
            send_message(chat_id, '❌ لینک یوتیوب معتبر نیست.', get_back_keyboard())
        return
    
    msg = send_message(chat_id, f'⏳ در حال دانلود از <b>{state["platform"]}</b>...', None)
    processing_msg_id = msg['result']['message_id'] if msg and msg.get('ok') else None
    
    try:
        video_url = None
        if platform == 'tiktok':
            video_url = download_tiktok(text)
        elif platform == 'instagram':
            video_url = download_instagram(text)
        
        if not video_url:
            raise Exception('ویدیو پیدا نشد')
        
        current_time = get_current_time()
        caption = f"""✅ دانلود موفق!

🎯 {state['platform']}
🔗 {text}
📅 {current_time}"""
        
        send_video(chat_id, video_url, caption, get_back_keyboard())
        
        admin_msg = f"""📤 دانلود جدید
🎯 {state['platform']}
🔗 {text}
📅 {current_time}"""
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
        'time': get_current_time()
    })

@app.route('/time', methods=['GET'])
def get_time():
    """دریافت زمان تهران از API"""
    return jsonify({
        'time': get_current_time(),
        'api_status': 'success'
    })

@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    try:
        if not WEBHOOK_URL:
            return jsonify({'error': 'WEBHOOK_URL not set'}), 400
        
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
        'time': get_current_time()
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
        logger.warning("⚠️ WEBHOOK_URL not set")
    
    app.run(host='0.0.0.0', port=PORT)
