from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    get_user, add_food_log, add_workout_log, add_water_log,
    get_today_food, get_today_workouts, get_week_workouts, get_today_water
)
from utils import calc_calories, calc_bmi, bmi_verdict, parse_food_with_ai, parse_water_with_ai
import random

waiting_food_input = 100
waiting_water_input = 101

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🍽 Добавить еду"), KeyboardButton("💧 Вода")],
        [KeyboardButton("💪 Тренировка"), KeyboardButton("📊 Мой профиль")],
    ],
    resize_keyboard=True,
)


def calc_water_norm(weight: float) -> float:
    """30-35 мл на кг веса"""
    return round(weight * 0.033, 1)


def progress_bar(current, target, length=10):
    if target <= 0:
        return "▓" * length
    filled = int(min(current / target, 1.0) * length)
    return "▓" * filled + "░" * (length - filled)


async def handle_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("Сначала зарегистрируйся — напиши /start")
        return ConversationHandler.END

    if text == "🍽 Добавить еду":
        await update.message.reply_text(
            "✍️ Напиши что ел, например:\n"
            "• 300г пельмени Мираторг\n"
            "• овсянка 200г с бананом\n"
            "• большой бургер из макдака",
        )
        return waiting_food_input

    elif text == "💧 Вода":
        norm = calc_water_norm(user["weight"])
        today = get_today_water(user_id)
        remaining = max(0, norm - today)
        await update.message.reply_text(
            f"💧 *Вода*\n\n"
            f"Сегодня выпито: *{today:.2f} л* из {norm} л\n"
            f"Осталось: *{remaining:.2f} л*\n\n"
            f"Напиши сколько выпил(а), например:\n"
            f"• `0.5` — просто поллитра воды\n"
            f"• `0.33 кола` — банка колы\n"
            f"• `0.25 сок апельсиновый`",
            parse_mode="Markdown"
        )
        return waiting_water_input

    elif text == "💪 Тренировка":
        await log_workout(update, ctx)

    elif text == "📊 Мой профиль":
        await show_profile(update, ctx)

    return ConversationHandler.END


async def log_food(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала зарегистрируйся — напиши /start")
        return ConversationHandler.END

    if update.message.text.startswith("/log"):
        food_text = update.message.text[4:].strip()
        if not food_text:
            await update.message.reply_text(
                "✍️ Напиши что ел после команды, например:\n`/log 300г пельмени`",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    else:
        food_text = update.message.text.strip()

    msg = await update.message.reply_text("🔍 Считаю КБЖУ...")
    result = await parse_food_with_ai(food_text)

    if not result:
        await msg.edit_text("❌ Не смог разобрать еду. Попробуй описать точнее.")
        return ConversationHandler.END

    add_food_log(user_id, food_text, result["calories"], result["protein"], result["fat"], result["carbs"])

    today = get_today_food(user_id)
    total_cal  = sum(r["calories"] for r in today)
    total_prot = sum(r["protein"]  for r in today)
    total_fat  = sum(r["fat"]      for r in today)
    total_carb = sum(r["carbs"]    for r in today)

    age = user["age"] if user["age"] else 30
    target = calc_calories(user["weight"], user["height"], user["gender"], user["goal_type"], user["goal_weight"], age)
    remaining = target - total_cal
    bar = progress_bar(total_cal, target)

    await msg.edit_text(
        f"✅ *Записано:* {food_text}\n"
        f"├ Калории: {result['calories']:.0f} ккал\n"
        f"├ Белки: {result['protein']:.1f}г\n"
        f"├ Жиры: {result['fat']:.1f}г\n"
        f"└ Углеводы: {result['carbs']:.1f}г\n\n"
        f"📊 *Итого за сегодня:*\n"
        f"{bar} {total_cal:.0f}/{target} ккал\n"
        f"Б: {total_prot:.1f}г  Ж: {total_fat:.1f}г  У: {total_carb:.1f}г\n\n"
        + (f"✊ Осталось набрать: {remaining:.0f} ккал" if remaining > 0 else f"⚠️ Превышение на {abs(remaining):.0f} ккал"),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def log_water(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return ConversationHandler.END

    text = update.message.text.strip()
    result = await parse_water_with_ai(text)

    if not result:
        await update.message.reply_text("❌ Не понял. Напиши например: `0.5` или `0.33 кола`", parse_mode="Markdown")
        return waiting_water_input

    add_water_log(user_id, result["amount"], result.get("note", ""))

    today = get_today_water(user_id)
    norm = calc_water_norm(user["weight"])
    remaining = max(0, norm - today)
    bar = progress_bar(today, norm)

    if today >= norm:
        status = "✅ Норма выполнена! Отличная работа 💧"
    elif remaining < 0.5:
        status = f"🔜 Почти! Осталось всего {remaining:.2f} л"
    else:
        status = f"💧 Осталось выпить: {remaining:.2f} л"

    note_line = f" ({result['note']})" if result.get("note") else ""

    await update.message.reply_text(
        f"✅ *Записано:* {result['amount']:.2f} л{note_line}\n\n"
        f"💧 *Вода сегодня:*\n"
        f"{bar} {today:.2f} / {norm} л\n\n"
        f"{status}",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def log_workout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала зарегистрируйся — напиши /start")
        return

    note = " ".join(ctx.args) if ctx.args else ""
    add_workout_log(user_id, note)
    week = get_week_workouts(user_id)

    phrases = [
        "🔥 Огонь! Так держать!",
        "💪 Ещё одна тренировка в копилку!",
        "🏆 Результат — это сумма усилий!",
        "⚡ Тело говорит спасибо!",
        "🚀 Прогресс не остановить!",
    ]

    await update.message.reply_text(
        f"✅ *Тренировка отмечена!*\n\n"
        f"{random.choice(phrases)}\n\n"
        f"За последние 7 дней: *{week}* тренировок",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


async def show_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала зарегистрируйся — напиши /start")
        return

    bmi = calc_bmi(user["weight"], user["height"])
    verdict = bmi_verdict(bmi, user["gender"])
    age = user["age"] if user["age"] else 30
    target_cal = calc_calories(user["weight"], user["height"], user["gender"], user["goal_type"], user["goal_weight"], age)

    today_food = get_today_food(user_id)
    total_cal  = sum(r["calories"] for r in today_food)
    total_prot = sum(r["protein"]  for r in today_food)
    total_fat  = sum(r["fat"]      for r in today_food)
    total_carb = sum(r["carbs"]    for r in today_food)

    today_water = get_today_water(user_id)
    water_norm = calc_water_norm(user["weight"])

    week_w = get_week_workouts(user_id)
    bar = progress_bar(total_cal, target_cal)
    water_bar = progress_bar(today_water, water_norm)
    diff = user["goal_weight"] - user["weight"]
    diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"
    age_line = f"🎂 Возраст: {user['age']} лет\n" if user["age"] else ""

    await update.message.reply_text(
        f"👤 *Мой профиль*\n\n"
        f"📏 Рост: {user['height']:.0f} см\n"
        f"⚖️ Вес: {user['weight']} кг\n"
        f"{age_line}"
        f"🎯 Цель: {user['goal_weight']} кг ({diff_str} кг)\n"
        f"🏃 Задача: {user['goal_type']}\n\n"
        f"📊 ИМТ: {bmi:.1f} — {verdict}\n"
        f"🍽 Норма калорий: ~{target_cal} ккал/день\n"
        f"💧 Норма воды: {water_norm} л/день\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 *Сегодня*\n"
        f"{bar} {total_cal:.0f}/{target_cal} ккал\n"
        f"Б: {total_prot:.1f}г  Ж: {total_fat:.1f}г  У: {total_carb:.1f}г\n"
        f"Приёмов пищи: {len(today_food)}\n\n"
        f"{water_bar} {today_water:.2f}/{water_norm} л воды\n\n"
        f"🏋️ Тренировок за 7 дней: {week_w}\n"
        f"⏰ Итог дня в: {user['notify_time']}",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )
