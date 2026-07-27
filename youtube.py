import os
import re
import asyncio
import yt_dlp
import imageio_ffmpeg
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LinkPreviewOptions
from telegram.ext import ContextTypes
from database import is_user_premium, check_and_use_promo

USER_DATA_CACHE = {}

def is_youtube_url(url: str) -> bool:
    if not url:
        return False
    clean_url = url.strip()
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|live/)?([\w-]{11})'
    return bool(re.search(youtube_regex, clean_url))

def get_video_info_fallback(url: str):
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
        print(f"🔥 yt-dlp tahlil xatosi: {e}")
        return None

async def get_video_info(url: str):
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(None, get_video_info_fallback, url)
    if not info:
        return None

    title = info.get('title', 'YouTube Video')
    vid_id = info.get('id', 'unknown')

    formats = info.get('formats', [])
    available_heights_in_video = set()

    for f in formats:
        h = f.get('height')
        vcodec = f.get('vcodec')
        if h and vcodec and vcodec != 'none':
            available_heights_in_video.add(h)

    # Siz so'ragan aniq standart qadamlar ro'yxati
    target_steps = [144, 240, 360, 480, 720, 1080, 1440, 2160]
    found_heights = []

    for target in target_steps:
        for h in available_heights_in_video:
            if abs(h - target) <= 30:
                if target not in found_heights:
                    found_heights.append(target)
                break

    if not found_heights:
        found_heights = [360, 720, 1080]

    return {
        "title": title,
        "height_sizes": found_heights,
        "video_id": vid_id
    }

async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    if is_youtube_url(text):
        try:
            await update.message.delete()
        except Exception:
            pass

        msg = await context.bot.send_message(
            chat_id=user_id,
            text="🔎 Video tahlil qilinmoqda...",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

        info = await get_video_info(text)

        if not info or not info.get("height_sizes"):
            await msg.edit_text(
                "❌ Videoni tahlil qilib bo'lmadi. Havolani tekshiring.",
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            return

        vid_id = info["video_id"]
        USER_DATA_CACHE[f"{user_id}_{vid_id}"] = text

        available_heights = info["height_sizes"]

        keyboard = []
        row = []

        for h in available_heights:
            if h == 1440:
                label = "2K ⭐️"
            elif h == 2160:
                label = "4K ⭐️"
            elif h >= 1080:
                label = f"{h}p ⭐️"
            else:
                label = f"{h}p"

            callback_data = f"dl_{vid_id}_{h}"
            row.append(InlineKeyboardButton(label, callback_data=callback_data))

            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        caption = (
            f"🎬 <b>{info['title']}</b>\n\n"
            f"📥 Kerakli yuklab olish sifatini tanlang:\n"
            f"<i>(⭐️ 1080p va undan yuqori sifatlar uchun Premium talab qilinadi)</i>"
        )

        await msg.edit_text(
            caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return

    promo_result = check_and_use_promo(user_id, text)
    if "🎉" in promo_result:
        await update.message.reply_text(promo_result)
    else:
        await update.message.reply_text("⚠️ Iltimos, to'g'ri YouTube havola yoki faol promo-kod yuboring!")

async def download_and_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    if not data.startswith("dl_"):
        return

    parts = data.split("_")
    if len(parts) < 3 or not parts[2].isdigit():
        await query.answer("❌ Xatolik: Eskirgan tugma.", show_alert=True)
        return

    vid_id = parts[1]
    height = int(parts[2])

    user_has_premium = is_user_premium(user_id)
    display_name = "2K" if height == 1440 else ("4K" if height == 2160 else f"{height}p")

    if height >= 1080 and not user_has_premium:
        await query.answer(f"⭐️ {display_name} sifati faqat Premium foydalanuvchilar uchun!", show_alert=True)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"⭐️ <b>{display_name}</b> uchun Premium obuna kerak!",
            parse_mode="HTML"
        )
        return

    await query.answer()

    cache_key = f"{user_id}_{vid_id}"
    url = USER_DATA_CACHE.get(cache_key, f"https://www.youtube.com/watch?v={vid_id}")

    status_msg = await context.bot.send_message(
        chat_id=user_id,
        text=f"⚡️ <b>{display_name}</b> sifatdagi video yuklanmoqda...",
        parse_mode="HTML"
    )

    output_filename = f"video_{user_id}_{height}_{vid_id}.mp4"

    def _download_task():

        if height >= 1080:
            format_string = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        else:
            format_string = f"best[height<={height}]/best"

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        ydl_opts = {
            'format': format_string,
            'outtmpl': output_filename,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_path,
            'cookiefile': 'cookies.txt',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return os.path.exists(output_filename)
        except Exception as e:
            print(f"🔥 Yuklash xatosi: {e}")
            return False

    try:
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, _download_task)

        if not success or not os.path.exists(output_filename):
            await status_msg.edit_text("❌ Videoni yuklab bo'lmadi. Havolani yoki formatni tekshiring.")
            return

        file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)

        if file_size_mb > 2000:
            await status_msg.edit_text(f"⚠️ Video hajmi juda katta ({file_size_mb:.1f} MB).")
            os.remove(output_filename)
            return

        await status_msg.edit_text("📤 Video Telegram'ga yuborilmoqda...")

        with open(output_filename, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=user_id,
                video=video_file,
                caption=f"✅ Video muvaffaqiyatli yuklab olindi! ({display_name})"
            )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik: <code>{e}</code>", parse_mode="HTML")

    finally:
        if os.path.exists(output_filename):
            try:
                os.remove(output_filename)
            except Exception:
                pass
