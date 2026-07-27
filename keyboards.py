from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_panel():
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users")
        ],
        [
            # MUTA'NOSIBLIK SHU YERDA: callback_data aynan "sub_menu" bo'lishi shart!
            InlineKeyboardButton("📢 Majburiy obuna", callback_data="sub_menu")
        ],
        [
            InlineKeyboardButton("➕ Promo qo'shish", callback_data="add_promo"),
            InlineKeyboardButton("🗑 Promo o'chirish", callback_data="del_promo")
        ],
        [
            InlineKeyboardButton("📨 Reklama", callback_data="send_ad")
        ],
        [
            InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)