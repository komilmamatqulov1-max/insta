from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADMINS
from database import (
    add_channel,
    remove_channel,
    get_all_channels,
    add_promo_code,
    remove_promo_by_index,
    get_all_promo_codes,
)
from states import (
    ADD_CHANNEL,
    REMOVE_CHANNEL,
    ADD_PROMO_CODE,
    ADD_PROMO_DAYS,
    DEL_PROMO_CODE,
)


# ==========================================
# MENYULAR (KEYBOARDS)
# ==========================================

def admin_panel_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users"),
        ],
        [
            InlineKeyboardButton("📢 Majburiy obuna", callback_data="sub_menu"),
            InlineKeyboardButton("🎁 Promo-kodlar", callback_data="promo_menu"),
        ],
        [
            InlineKeyboardButton("📨 Reklama", callback_data="send_ad"),
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def sub_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_sub_channel")],
        [InlineKeyboardButton("🗑 Kanal o'chirish", callback_data="del_sub_channel")],
        [InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_sub_channels")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(keyboard)


def promo_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Promo-kod qo'shish", callback_data="add_promo")],
        [InlineKeyboardButton("🗑 Promo-kod o'chirish", callback_data="del_promo")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# ASOSIY ADMIN PANEL VA MENYULAR
# ==========================================

async def open_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Siz admin emassiz.")
        return

    await update.message.reply_text(
        "👑 <b>ADMIN PANEL</b>",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard(),
    )


async def sub_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_admin":
        try:
            await query.edit_message_text(
                "👑 <b>ADMIN PANEL</b>",
                parse_mode="HTML",
                reply_markup=admin_panel_keyboard(),
            )
        except Exception:
            pass
        return

    channels = get_all_channels()
    text = "📢 <b>Majburiy obuna sozlamalari</b>\n\n"
    if channels:
        text += "Hozirgi aktiv kanallar:\n"
        for ch_id, ch_link in channels:
            text += f"• <b>{ch_id}</b> — <a href='{ch_link}'>Havolaga o'tish</a>\n"
    else:
        text += "Hozircha hech qanday kanal qo'shilmagan."

    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=sub_menu_keyboard(),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def promo_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.edit_message_text(
            "🎁 <b>Promo-kodlar bo'limi</b>\n\n"
            "Yangi promo-kod yaratishingiz yoki eskisini o'chirishingiz mumkin:",
            parse_mode="HTML",
            reply_markup=promo_menu_keyboard(),
        )
    except Exception:
        pass


# ==========================================
# KANAL QO'SHISH VA O'CHIRISH
# ==========================================

async def start_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "➕ <b>Yangi kanal qo'shish</b>\n\n"
        "Menga kanal username'i va linkini quyidagi formatda yuboring:\n\n"
        "<code>@kanal_username https://t.me/kanal_link</code>"
    )

    try:
        await query.edit_message_text(text, parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML")
    return ADD_CHANNEL


async def save_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.strip().split()

    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Xato format! Qaytadan urinib ko'ring:\n<code>@username https://t.me/link</code>",
            parse_mode="HTML",
        )
        return ADD_CHANNEL

    ch_id, ch_link = parts[0], parts[1]

    success = add_channel(ch_id, ch_link)
    if success:
        await update.message.reply_text(
            f"✅ <b>{ch_id}</b> kanali muvaffaqiyatli bazaga qo'shildi!",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ Bu kanal allaqachon bazada bor yoki xatolik yuz berdi.",
            reply_markup=admin_panel_keyboard(),
        )

    return ConversationHandler.END


async def start_del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🗑 <b>Kanalni o'chirish</b>\n\n"
        "O'chirmoqchi bo'lgan kanalingiz username'ini yuboring:\n"
        "<i>Masalan: @Nurjahon_Pubg</i>"
    )

    try:
        await query.edit_message_text(text, parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML")
    return REMOVE_CHANNEL


async def remove_channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch_id = update.message.text.strip()

    success = remove_channel(ch_id)
    if success:
        await update.message.reply_text(
            f"🗑 <b>{ch_id}</b> bazadan o'chirildi!",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ Bunday kanal topilmadi.", reply_markup=admin_panel_keyboard()
        )

    return ConversationHandler.END


# ==========================================
# PROMO-KOD QO'SHISH VA O'CHIRISH
# ==========================================

async def start_add_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "➕ <b>Yangi promo-kod yaratish</b>\n\nPromo-kod nomini kiriting:"
    try:
        await query.edit_message_text(text, parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML")
    return ADD_PROMO_CODE


async def get_promo_code_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_text = update.message.text.strip()
    context.user_data["new_promo_code"] = code_text

    await update.message.reply_text(
        f"🔑 Promo-kod: <b>{code_text}</b>\n\n"
        "Endi ushbu promo-kod necha KUN Premium berishini kiriting (masalan: <code>30</code>):",
        parse_mode="HTML",
    )
    return ADD_PROMO_DAYS


async def save_promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days_text = update.message.text.strip()

    if not days_text.isdigit():
        await update.message.reply_text(
            "❌ Iltimos, faqat raqam kiriting (masalan: 7, 30)!"
        )
        return ADD_PROMO_DAYS

    code = context.user_data.get("new_promo_code")
    days = int(days_text)

    success = add_promo_code(code, days)
    if success:
        await update.message.reply_text(
            f"✅ <b>Promo-kod yaratildi!</b>\n\n"
            f"🎫 Kod: <code>{code}</code>\n"
            f"⏰ Muddati: <b>{days} kun</b>",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ Bunday promo-kod allaqachon mavjud!",
            reply_markup=admin_panel_keyboard(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def start_del_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    promos = get_all_promo_codes()

    if not promos:
        text = "❌ Hozircha aktiv promo-kodlar mavjud emas."
        try:
            await query.edit_message_text(text, reply_markup=promo_menu_keyboard())
        except Exception:
            await query.message.reply_text(text, reply_markup=promo_menu_keyboard())
        return ConversationHandler.END

    text = "🗑 <b>Aktiv promo-kodlar ro'yxati:</b>\n\n"
    for idx, (code, days) in enumerate(promos, start=1):
        text += f"<b>{idx}.</b> Kod: <code>{code}</code> — ({days} kun)\n"

    text += "\nO'chirmoqchi bo'lgan promo-kodning <b>tartib raqamini</b> yuboring (masalan: <code>1</code>):"

    try:
        await query.edit_message_text(text, parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML")

    return DEL_PROMO_CODE


async def remove_promo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ Iltimos, faqat raqam kiriting (masalan: 1, 2, 3...)!"
        )
        return DEL_PROMO_CODE

    index = int(text) - 1
    deleted_code = remove_promo_by_index(index)

    if deleted_code:
        await update.message.reply_text(
            f"✅ <b>{deleted_code}</b> promo-kodi muvaffaqiyatli o'chirildi!",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text(
            "❌ Bunday raqamdagi promo-kod topilmadi. Ro'yxatni qaytadan tekshiring.",
            reply_markup=admin_panel_keyboard(),
        )

    return ConversationHandler.END


# ==========================================
# UMUMIY BEKOR QILISH
# ==========================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bekor qilindi.", reply_markup=admin_panel_keyboard()
    )
    return ConversationHandler.END