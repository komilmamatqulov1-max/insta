# from gorizontal import handle_16_9_text, download_and_send_16_9
from insta import is_instagram_url, get_insta_video_info
from youtube import handle_user_text, download_and_send_video, USER_DATA_CACHE
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ChatJoinRequestHandler,
    ContextTypes,
    filters,
)

# Konfiguratsiya va Baza
from config import TOKEN, ADMINS
from database import init_db, add_user, get_users_count

# Obuna moduli
from subscribe import (
    check_user_subscriptions,
    get_sub_keyboard,
    check_button_callback,
    track_join_request,
)

# Holatlar (States)
from states import (
    ADD_CHANNEL,
    REMOVE_CHANNEL,
    ADD_PROMO_CODE,
    ADD_PROMO_DAYS,
    DEL_PROMO_CODE,
)

# Admin va Tugmalar
from admin import (
    sub_menu_callback,
    promo_menu_callback,
    start_add_channel,
    save_channel_handler,
    start_del_channel,
    remove_channel_handler,
    start_add_promo,
    get_promo_code_name,
    save_promo_handler,
    start_del_promo,
    remove_promo_handler,
    cancel,
    admin_panel_keyboard,
)

# Bot ishga tushishi bilan bazani va jadvallarni tayyorlaymiz
init_db()


# ==========================================
# KOMANDALAR: /start, /id, /admin
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)

    is_subscribed = await check_user_subscriptions(user.id, context)

    if is_subscribed:
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\n"
            "🎥 YouTube & Instagram Save Bot ga xush kelibsiz.\n"
            "Menga video havolasini yuboring!"
        )
    else:
        await update.message.reply_text(
            "⚠️ Botdan foydalanish uchun avval quyidagi kanallarga obuna bo'ling:",
            reply_markup=get_sub_keyboard(),
        )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Sizning ID:\n{update.effective_user.id}"
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Siz admin emassiz.")
        return

    await update.message.reply_text(
        "👑 <b>ADMIN PANEL</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(),
    )


# ==========================================
# INSTAGRAM VA YOUTUBE MATNLARINI YO'NALTIRUVCHI ROUTER
# ==========================================

async def handle_combined_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    # 1. Agar Instagram havolasi bo'lsa
    if is_instagram_url(text):
        try:
            await update.message.delete()
        except Exception:
            pass

        msg = await context.bot.send_message(
            chat_id=user_id,
            text="🔎 Instagram media tahlil qilinmoqda...",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

        info = await get_insta_video_info(text)

        if not info or not info.get("height_sizes"):
            await msg.edit_text(
                "❌ Instagram videoni tahlil qilib bo'lmadi. Havolani tekshiring.",
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            return

        vid_id = info["video_id"]
        USER_DATA_CACHE[f"{user_id}_{vid_id}"] = text

        available_heights = info["height_sizes"]
        keyboard = []
        row = []

        for h in available_heights:
            label = f"{h}p ⭐️" if h >= 1080 else f"{h}p"
            callback_data = f"dl_{vid_id}_{h}"
            row.append(InlineKeyboardButton(label, callback_data=callback_data))

            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        caption = (
            f"📸 <b>{info['title']}</b>\n\n"
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

    # 2. Aks holda YouTube yoki promo-kod uchun youtube.py dagi funksiyaga yuboramiz
    await handle_user_text(update, context)


# ==========================================
# ODDIY TUGMALAR (INLINE KEYBOARD)
# ==========================================

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Obunani tekshirish tugmasi
    if query.data == "check_subscription":
        await check_button_callback(update, context)
        return

    # Premium sifat bosilganda ogohlantirish
    if query.data.startswith("nobuy_"):
        await query.answer("⭐️ Ushbu sifat (1080p+) faqat Premium foydalanuvchilar uchun!", show_alert=True)
        return

    await query.answer()

    if query.data == "stats":
        users = get_users_count()
        await query.edit_message_text(
            f"📊 <b>Statistika</b>\n\n👥 Jami foydalanuvchilar: {users}",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard(),
        )
    elif query.data == "users":
        users = get_users_count()
        await query.edit_message_text(
            f"👥 Bazada {users} ta foydalanuvchi mavjud.",
            reply_markup=admin_panel_keyboard(),
        )


# ==========================================
# ASOSIY ISHGA TUSHIRISH QISMI
# ==========================================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # 1. Majburiy obuna ConversationHandler
    channel_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_channel, pattern="^add_sub_channel$"),
            CallbackQueryHandler(start_del_channel, pattern="^del_sub_channel$"),
        ],
        states={
            ADD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_channel_handler)],
            REMOVE_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_channel_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # 2. Promo-kod ConversationHandler
    promo_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_promo, pattern="^add_promo$"),
            CallbackQueryHandler(start_del_promo, pattern="^del_promo$"),
        ],
        states={
            ADD_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_code_name)],
            ADD_PROMO_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_promo_handler)],
            DEL_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_promo_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # 3. Handlerlarni ulash (TARTIBGA E'TIBOR BERING)

    # Yopiq kanal so'rovlarini tutish
    app.add_handler(ChatJoinRequestHandler(track_join_request))

    # Komandalar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(CommandHandler("admin", admin))

    # Conversation Handler'lar
    app.add_handler(channel_conv)
    app.add_handler(promo_conv)

    # 📌 YOUTUBE/INSTAGRAM YUKLASH TUGMALARINI TUTUVCHI HANDLER (dl_ bilan boshlanuvchi tugmalar uchun)
    app.add_handler(CallbackQueryHandler(download_and_send_video, pattern="^dl_"))

    # Menyu va admin callback'lari
    app.add_handler(CallbackQueryHandler(promo_menu_callback, pattern="^promo_menu$"))
    app.add_handler(CallbackQueryHandler(sub_menu_callback, pattern="^(sub_menu|back_to_admin)$"))
    app.add_handler(CallbackQueryHandler(admin_buttons))

    # 📌 Instagram, YouTube linklarini va Promo-kodlarni tutuvchi asosiy handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_combined_text))

    print("✅ Bot muvaffaqiyatli ishga tushdi.")
    app.run_polling()


if __name__ == "__main__":
    main()