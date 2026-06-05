from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import upsert_user, get_user
from utils import calc_bmi, bmi_verdict, calc_calories

GENDER, HEIGHT, WEIGHT, GOAL_WEIGHT, GOAL_TYPE, NOTIFY_TIME, AGE = range(7)

GOAL_TYPES = {
    "1": "похудеть",
    "2": "набрать мышечную массу",
    "3": "снизить процент жира",
    "4": "набрать общий вес",
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🍽 Добавить еду"), KeyboardButton("💪 Тренировка")],
        [KeyboardButton("📊 Мой профиль")],
    ],
    resize_keyboard=True,
)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        "👋 Привет! Я твой персональный фитнес-помощник.\n\n"
        "Буду следить за твоим питанием и тренировками 💪\n\n"
        "Укажи свой *пол* — напиши *м* или *ж*:",
        parse_mode="Markdown"
    )
    return GENDER


async def get_gender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text not in ("м", "ж", "m", "f"):
        await update.message.reply_text("Напиши *м* (мужской) или *ж* (женский):", parse_mode="Markdown")
        return GENDER
    ctx.user_data["gender"] = "male" if text in ("м", "m") else "female"
    await update.message.reply_text("📏 Напиши свой *рост* в сантиметрах (например: 175):", parse_mode="Markdown")
    return HEIGHT


async def get_height(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        h = float(update.message.text.replace(",", "."))
        assert 100 <= h <= 250
    except:
        await update.message.reply_text("Введи корректный рост (например: 175):")
        return HEIGHT
    ctx.user_data["height"] = h
    await update.message.reply_text("⚖️ Напиши свой текущий *вес* в кг (например: 70):", parse_mode="Markdown")
    return WEIGHT


async def get_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        w = float(update.message.text.replace(",", "."))
        assert 30 <= w <= 300
    except:
        await update.message.reply_text("Введи корректный вес (например: 70):")
        return WEIGHT
    ctx.user_data["weight"] = w
    await update.message.reply_text("🎯 Какой *целевой вес*? (в кг, например: 65):", parse_mode="Markdown")
    return GOAL_WEIGHT


async def get_goal_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        gw = float(update.message.text.replace(",", "."))
        assert 30 <= gw <= 300
    except:
        await update.message.reply_text("Введи корректный целевой вес (например: 65):")
        return GOAL_WEIGHT
    ctx.user_data["goal_weight"] = gw
    await update.message.reply_text(
        "💡 Выбери *основную цель*:\n\n"
        "1️⃣ Похудеть\n"
        "2️⃣ Набрать мышечную массу\n"
        "3️⃣ Снизить процент жира\n"
        "4️⃣ Набрать общий вес\n\n"
        "Напиши цифру от 1 до 4:",
        parse_mode="Markdown"
    )
    return GOAL_TYPE


async def get_goal_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in GOAL_TYPES:
        await update.message.reply_text("Напиши цифру от 1 до 4:")
        return GOAL_TYPE
    ctx.user_data["goal_type"] = GOAL_TYPES[text]
    await update.message.reply_text(
        "🎂 Сколько тебе *лет*? (например: 25)\n\n"
        "_Нужно для точного расчёта калорий_",
        parse_mode="Markdown"
    )
    return AGE


async def get_age(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        assert 10 <= age <= 100
    except:
        await update.message.reply_text("Введи корректный возраст (например: 25):")
        return AGE
    ctx.user_data["age"] = age
    await update.message.reply_text(
        "🕐 В какое время присылать *ежедневный итог*?\n\n"
        "Напиши в формате ЧЧ:ММ (например: 21:00):",
        parse_mode="Markdown"
    )
    return NOTIFY_TIME


async def get_notify_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        parts = text.split(":")
        assert len(parts) == 2
        hh, mm = int(parts[0]), int(parts[1])
        assert 0 <= hh <= 23 and 0 <= mm <= 59
        notify_time = f"{hh:02d}:{mm:02d}"
    except:
        await update.message.reply_text("Введи время в формате ЧЧ:ММ (например: 21:00):")
        return NOTIFY_TIME

    user = update.effective_user
    d = ctx.user_data
    upsert_user(
        user.id, user.username or user.first_name,
        gender=d["gender"],
        height=d["height"],
        weight=d["weight"],
        goal_weight=d["goal_weight"],
        goal_type=d["goal_type"],
        age=d["age"],
        notify_time=notify_time,
    )

    bmi = calc_bmi(d["weight"], d["height"])
    verdict = bmi_verdict(bmi, d["gender"])
    calories = calc_calories(d["weight"], d["height"], d["gender"], d["goal_type"], d["goal_weight"], d["age"])
    diff = d["goal_weight"] - d["weight"]
    diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"

    await update.message.reply_text(
        f"✅ *Профиль создан!*\n\n"
        f"👤 Пол: {'Мужской' if d['gender']=='male' else 'Женский'}\n"
        f"📏 Рост: {d['height']:.0f} см\n"
        f"⚖️ Вес: {d['weight']} кг\n"
        f"🎂 Возраст: {d['age']} лет\n"
        f"🎯 Цель: {d['goal_weight']} кг ({diff_str} кг) — {d['goal_type']}\n\n"
        f"📊 *Твой ИМТ:* {bmi:.1f} — {verdict}\n\n"
        f"🍽 *Норма калорий:* ~{calories} ккал/день\n\n"
        f"⏰ Итог буду присылать в *{notify_time}*",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


# Обработчик для существующих пользователей без возраста
async def ask_age_existing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎂 Привет! Хочу уточнить твой *возраст* для точного расчёта калорий.\n\n"
        "Напиши сколько тебе лет (например: 25):",
        parse_mode="Markdown"
    )
    return AGE


async def save_age_existing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        assert 10 <= age <= 100
    except:
        await update.message.reply_text("Введи корректный возраст (например: 25):")
        return AGE

    user = update.effective_user
    upsert_user(user.id, user.username or user.first_name, age=age)

    await update.message.reply_text(
        f"✅ Возраст сохранён — *{age} лет*!\n\n"
        "Теперь расчёт калорий стал точнее 💪",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END
