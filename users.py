from telegram import Update
from telegram.ext import ContextTypes

from database import add_user


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    add_user(update.effective_user)

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "🎥 YouTube Save Bot ga xush kelibsiz."
    )


# =========================
# MY ID
# =========================

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"🆔 Sizning ID:\n{update.effective_user.id}"
    )