from telegram import Update
from telegram.ext import ContextTypes
from database import get_all_users
from config import ADMIN_IDS


async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Использование: /broadcast текст сообщения")
        return
    users = get_all_users()
    ok = 0
    for u in users:
        try:
            await ctx.bot.send_message(u["user_id"], text)
            ok += 1
        except:
            pass
    await update.message.reply_text(f"Отправлено {ok}/{len(users)}")
