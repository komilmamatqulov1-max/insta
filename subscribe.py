from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import get_all_channels, add_join_request, check_join_request


# ⚠️ MANA SHU FUNKSIYA YETISHMAYOTGAN EDI:
async def track_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi yopiq kanalga obuna so'rovi yuborganda ishlaydi"""
    request = update.chat_join_request
    user_id = request.from_user.id

    # Kanal username va ID'sini bazaga saqlaymiz
    if request.chat.username:
        add_join_request(user_id, f"@{request.chat.username}")
    add_join_request(user_id, str(request.chat.id))
    print(f"✅ So'rov saqlandi: User {user_id} -> Chat {request.chat.id}")


async def check_user_subscriptions(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Foydalanuvchi obuna bo'lganini yoki so'rov yuborganini tekshiradi"""
    channels = get_all_channels()

    if not channels:
        return True

    for ch_id, ch_link in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)

            # 1. Kanalda a'zo bo'lsa
            if member.status in ['member', 'administrator', 'creator']:
                continue

            # 2. Kanalda bo'lmasa, so'rov yuborganini tekshiramiz
            if check_join_request(user_id, ch_id):
                continue

            return False
        except Exception as e:
            print(f"⚠️ Obuna tekshirishda xatolik ({ch_id}): {e}")
            if check_join_request(user_id, ch_id):
                continue
            return False

    return True


def get_sub_keyboard():
    """Kanallar uchun Inline knopkalar"""
    channels = get_all_channels()
    keyboard = []

    for idx, (ch_id, ch_link) in enumerate(channels, 1):
        keyboard.append([InlineKeyboardButton(f"📢 {idx}-Kanalga o'tish", url=ch_link)])

    keyboard.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)


async def check_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'✅ Tekshirish' tugmasi bosilganda ishlaydi"""
    query = update.callback_query
    user_id = query.from_user.id

    is_subscribed = await check_user_subscriptions(user_id, context)

    if is_subscribed:
        await query.answer("✅ Rahmat! Obuna/So'rov tasdiqlandi.", show_alert=True)
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(
            chat_id=user_id,
            text="👋 Assalomu alaykum!\n\n🎥 YouTube Save Bot ga xush kelibsiz."
        )
    else:
        await query.answer("⚠️ Hali kanalga obuna bo'lmadingiz yoki so'rov yubormadingiz!", show_alert=True)