import os
import re
import asyncio
import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LinkPreviewOptions
from database import is_user_premium

# Instagram havolasini tekshiruvchi regex
def is_instagram_url(url: str) -> bool:
    if not url:
        return False
    clean_url = url.strip()
    pattern = r'(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w-]+'
    return bool(re.search(pattern, clean_url))

def get_insta_video_info_fallback(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"🔥 Instagram tahlil xatosi: {e}")
        return None

async def get_insta_video_info(url: str):
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, get_insta_video_info_fallback, url)
    if not info:
        return None

    title = info.get('title', info.get('description', 'Instagram Video'))
    vid_id = info.get('id', 'unknown_insta')

    formats = info.get('formats', [])
    available_heights_in_video = set()

    for f in formats:
        h = f.get('height')
        vcodec = f.get('vcodec')
        if h and vcodec and vcodec != 'none':
            available_heights_in_video.add(h)

    # Barcha kerakli qadamlar (144p dan 4K gacha)
    target_steps = [144, 240, 360, 480, 720, 1080, 1440, 2160]  # 1440 = 2K, 2160 = 4K
    found_heights = []

    for target in target_steps:
        for h in available_heights_in_video:
            if abs(h - target) <= 40:  # Farq yaqin bo'lsa topib oladi
                if target not in found_heights:
                    found_heights.append(target)
                break

    # Agar videoda o'lchamlar aniqlanmasa, eng ommaboplarini chiqaramiz
    if not found_heights:
        found_heights = [360, 480, 720, 1080]

    return {
        "title": title[:50] if title else "Instagram Video",
        "height_sizes": found_heights,
        "video_id": vid_id
    }

# --- YUKLAB OLISH FUNKSIYASI (144p dan 4K gacha va FFmpeg birlashtirishi bilan) ---
def download_insta_video_sync(url: str, quality: int, output_template: str):
    """
    Tanlangan sifat (144, 240, 360, 480, 720, 1080, 1440(2K), 2160(4K)) 
    bo'yicha video va ovozni to'g'ri birlashtirib yuklaydi.
    """
    ydl_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_filename = base + ".mp4"
            if os.path.exists(mp4_filename):
                return mp4_filename
            return filename
    except Exception as e:
        print(f"🔥 Yuklab olish xatosi: {e}")
        return None

async def download_insta_video(url: str, quality: int, output_template: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, download_insta_video_sync, url, quality, output_template)
