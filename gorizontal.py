# import os
# import re
# import asyncio
# import yt_dlp
# from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LinkPreviewOptions
# from telegram.ext import ContextTypes
# from database import is_user_premium
#
# # Vaqtinchalik havolalarni saqlash uchun kesh
# USER_169_CACHE = {}
#
#
# def is_youtube_url(url: str) -> bool:
#     """Yuborilgan matn YouTube havolasi ekanligini tekshirish"""
#     if not url:
#         return False
#     clean_url = url.strip()
#     youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|shorts/|live/)?([\w-]{11})'
#     return bool(re.search(youtube_regex, clean_url))
#
#
# def extract_horizontal_info(url: str):
#     """YouTube videodan mavjud sifatlar va sarlavhani ajratib olish (Sinxron)"""
#     ydl_opts = {
#         'quiet': True,
#         'no_warnings': True,
#         'socket_timeout': 15,
#         'nocheckcertificate': True,
#         'http_headers': {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#         }
#     }
#
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             if not info:
#                 return None
#
#             title = info.get('title', 'YouTube Video')
#             vid_id = info.get('id', 'unknown')
#             formats = info.get('formats', [])
#
#             available_heights = set()
#             for f in formats:
#                 h = f.get('height')
#                 vcodec = f.get('vcodec')
#                 if h and vcodec and vcodec != 'none':
#                     available_heights.add(h)
#
#             # Standart sifat qadamlari
#             standard_steps = [144, 240, 360, 480, 720, 1080, 1440, 2160]
#             found_heights = []
#
#             for step in standard_steps:
#                 for h in available_heights:
#                     if abs(h - step) <= 25:
#                         if step not in found_heights:
#                             found_heights.append(step)
#                         break
#
#             if not found_heights:
#                 found_heights = [360, 720, 1080]
#
#             return {
#                 "title": title,
#                 "heights": sorted(found_heights),
#                 "video_id": vid_id
#             }
#     except Exception as e:
#         print(f"🔥 Info olishda xatolik: {e}")
#         return None
#
#
# def download_video_sync(url: str, height: int, output_path: str) -> bool:
#     """
#     yt-dlp orqali videoni yuklab olish (Sinxron funksiya).
#     FFmpeg avtomatik ravishda video va audioni birlashtiradi.
#     """
#     format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
#
#     ydl_opts = {
#         'format': format_str,
#         'outtmpl': output_path,
#         'quiet': True,
#         'no_warnings': True,
#         'merge_output_format': 'mp4',
#         'socket_timeout': 40,
#         'nocheckcertificate': True,
#         'http_headers': {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
#         }
#     }
#
#     try:
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             ydl.download([url])
#         return os.path.exists(output_path) and os.path.getsize(output_path) > 0
#     except Exception as e:
#         print(f"🔥 Yuklash xatosi: {e}")
#         return False
#
#
# async def handle_16_9_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Foydalanuvchi havola yuborganda ishlaydigan handler"""
#     if not update.message or not update.message.text:
#         return
#
#     text = update.message.text.strip()
#     user_id = update.effective_user.id
#
#     if not is_youtube_url(text):
#         return
#
#     msg = await context.bot.send_message(
#         chat_id=user_id,
#         text="🖥 Video tahlil qilinmoqda...",
#         link_preview_options=LinkPreviewOptions(is_disabled=True)
#     )
#
#     loop = asyncio.get_running_loop()
#     info = await loop.run_in_executor(None, extract_horizontal_info, text)
#
#     if not info:
#         await msg.edit_text("❌ Video ma'lumotlarini olib bo'lmadi. Havola noto'g'ri yoki video yopiq bo'lishi mumkin.")
#         return
#
#     vid_id = info["video_id"]
#     USER_169_CACHE[f"{user_id}_{vid_id}"] = text
#
#     heights = info["heights"]
#     keyboard = []
#     row = []
#
#     for h in heights:
#         if h == 1440:
#             label = "2K ⭐️"
#         elif h == 2160:
#             label = "4K ⭐️"
#         elif h >= 1080:
#             label = f"{h}p ⭐️"
#         else:
#             label = f"{h}p"
#
#         callback_data = f"dl169_{vid_id}_{h}"
#         row.append(InlineKeyboardButton(label, callback_data=callback_data))
#
#         if len(row) == 2:
#             keyboard.append(row)
#             row = []
#
#     if row:
#         keyboard.append(row)
#
#     caption = (
#         f"🎬 <b>{info['title']}</b>\n\n"
#         f"📥 Kerakli video sifatini tanlang:\n"
#         f"<i>(⭐️ 1080p va undan yuqori sifatlar uchun Premium obuna kerak)</i>"
#     )
#
#     await msg.edit_text(
#         caption,
#         parse_mode="HTML",
#         reply_markup=InlineKeyboardMarkup(keyboard),
#         link_preview_options=LinkPreviewOptions(is_disabled=True)
#     )
#
#
# async def download_and_send_16_9(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Sifat tugmasi bosilganda yuklaydigan handler"""
#     query = update.callback_query
#     user_id = query.from_user.id
#     data = query.data
#
#     if not data.startswith("dl169_"):
#         return
#
#     parts = data.split("_")
#     if len(parts) < 3:
#         await query.answer("❌ Xatolik yuz berdi.", show_alert=True)
#         return
#
#     vid_id = parts[1]
#     height = int(parts[2])
#
#     user_has_premium = is_user_premium(user_id)
#     display_name = "2K" if height == 1440 else ("4K" if height == 2160 else f"{height}p")
#
#     if height >= 1080 and not user_has_premium:
#         await query.answer(f"⭐️ {display_name} sifati Premium foydalanuvchilar uchun!", show_alert=True)
#         return
#
#     await query.answer()
#
#     cache_key = f"{user_id}_{vid_id}"
#     url = USER_169_CACHE.get(cache_key, f"https://www.youtube.com/watch?v={vid_id}")
#
#     status_msg = await context.bot.send_message(
#         chat_id=user_id,
#         text=f"⚡️ <b>{display_name}</b> sifatdagi video yuklanmoqda...",
#         parse_mode="HTML"
#     )
#
#     output_filename = f"video_{user_id}_{vid_id}_{height}.mp4"
#
#     try:
#         loop = asyncio.get_running_loop()
#         success = await loop.run_in_executor(
#             None,
#             download_video_sync,
#             url,
#             height,
#             output_filename
#         )
#
#         if not success or not os.path.exists(output_filename):
#             await status_msg.edit_text("❌ Videoni yuklab bo'lmadi. Video bloklangan bo'lishi mumkin.")
#             return
#
#         file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
#
#         if file_size_mb > 1900:  # Telegram cheklovi (~2GB)
#             await status_msg.edit_text(f"⚠️ Video hajmi juda katta ({file_size_mb:.1f} MB). Telegram'ga yuborib bo'lmaydi.")
#             return
#
#         await status_msg.edit_text("📤 Video Telegram'ga yuklanmoqda...")
#
#         with open(output_filename, 'rb') as video_file:
#             await context.bot.send_video(
#                 chat_id=user_id,
#                 video=video_file,
#                 caption=f"✅ <b>{display_name}</b> sifatdagi video yuklandi!",
#                 parse_mode="HTML",
#                 read_timeout=300,
#                 write_timeout=300,
#                 connect_timeout=60
#             )
#
#         await status_msg.delete()
#
#     except Exception as e:
#         print(f"🔥 Telegram'ga yuborishda xatolik: {e}")
#         await status_msg.edit_text(f"❌ Xatolik yuz berdi: <code>{e}</code>", parse_mode="HTML")
#
#     finally:
#         # Faylni o'chirish (fayl qolib ketmasligi uchun)
#         if os.path.exists(output_filename):
#             try:
#                 os.remove(output_filename)
#             except Exception:
#                 pass