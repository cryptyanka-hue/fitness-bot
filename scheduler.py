import logging
import random
from datetime import datetime
from database import get_all_users, get_today_food, get_today_workouts, get_users_without_age
from utils import calc_calories

logger = logging.getLogger(__name__)

MOTIVATIONAL_QUOTES = [
    "💪 Каждый день — это шанс стать лучше.",
    "🔥 Дисциплина важнее мотивации.",
    "🏆 Маленькие шаги ведут к большим результатам.",
    "⚡ Тело достигает того, во что верит разум.",
    "🌟 Ты уже лучше, чем вчера — продолжай!",
    "🚀 Успех — это сумма ежедневных усилий.",
    "💡 Не останавливайся. Цель близко.",
]

MEAL_REMINDERS = {
    "08:00": "🌅 Привет! Ты уже позавтракал(а)? Не забудь записать завтрак через 🍽 Добавить еду",
    "13:00": "☀️ Время обеда! Не забудь записать что ел(а)",
    "19:00": "🌆 Ужинал(а) сегодня? Не забудь записать ужин",
}

WORKOUT_ROASTS = [
    "😤 Эй, за эту неделю {} тренировок из 3! Диван засасывает? Пора встать и пойти!",
    "🛋 {} тренировок за неделю... Ты точно помнишь зачем регистрировался(ась)?",
    "😅 Неделя прошла, тренировок: {}. Твои мышцы уже забыли как это — работать.",
    "🐌 {} тренировок за 7 дней. Цель сама себя не достигнет, давай!",
]

NUTRITION_ROASTS = [
    "🍕 Питание в норме только {} дней из 7. Бот следит — и он разочарован.",
    "😬 Только {} дней нормального питания за неделю. Так цели не достичь!",
    "📉 Калории в норме {} дней из 7. Хаотичное питание — враг прогресса!",
    "🤦 {} дней из 7 ты питался(ась) правильно. Остальные дни — загадка.",
]


async def ask_age_for_users(context):
    """Разослать запрос возраста существующим пользователям без него."""
    bot = context.bot
    users = get_users_without_age()
    for user in users:
        try:
            await bot.send_message(
                user["user_id"],
                "👋 Привет! Хочу уточнить твой *возраст* для точного расчёта нормы калорий.\n\n"
                "Напиши команду /setage и укажи свой возраст.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Cannot ask age to {user['user_id']}: {e}")


async def setup_scheduler(context):
    bot = context.bot
    now = datetime.now()
    hhmm = now.strftime("%H:%M")
    users = get_all_users()

    for user in users:
        if user["notify_time"] == hhmm:
            await send_daily_summary(bot, user)

    if hhmm in MEAL_REMINDERS:
        for user in users:
            try:
                await bot.send_message(user["user_id"], MEAL_REMINDERS[hhmm])
            except Exception as e:
                logger.warning(f"Cannot send meal reminder to {user['user_id']}: {e}")

    if now.weekday() == 6 and hhmm == "20:00":
        for user in users:
            await send_weekly_roast(bot, user)


async def send_daily_summary(bot, user):
    user_id = user["user_id"]
    today_food = get_today_food(user_id)
    total_cal  = sum(r["calories"] for r in today_food)
    total_prot = sum(r["protein"]  for r in today_food)
    total_fat  = sum(r["fat"]      for r in today_food)
    total_carb = sum(r["carbs"]    for r in today_food)
    workouts   = get_today_workouts(user_id)

    age = user["age"] if user["age"] else 30
    target = calc_calories(user["weight"], user["height"], user["gender"], user["goal_type"], user["goal_weight"], age)
    diff = total_cal - target
    quote = random.choice(MOTIVATIONAL_QUOTES)

    if diff < -200:
        cal_line = f"⚠️ Недобор: {abs(diff):.0f} ккал. Покушай ещё!"
    elif diff > 200:
        cal_line = f"⚠️ Перебор: {diff:.0f} ккал. Завтра поосторожнее."
    else:
        cal_line = "✅ Отлично! Попал(а) в норму."

    workout_line = f"🏋️ Тренировок сегодня: {workouts}" if workouts > 0 else "😴 Сегодня без тренировки."

    text = (
        f"📋 *Итог дня*\n\n"
        f"🍽 Калории: {total_cal:.0f} / {target} ккал\n"
        f"Б: {total_prot:.1f}г  Ж: {total_fat:.1f}г  У: {total_carb:.1f}г\n"
        f"{cal_line}\n\n"
        f"{workout_line}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{quote}"
    )

    try:
        await bot.send_message(user_id, text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Cannot send summary to {user_id}: {e}")


async def send_weekly_roast(bot, user):
    from database import get_conn
    user_id = user["user_id"]
    age = user["age"] if user["age"] else 30
    target = calc_calories(user["weight"], user["height"], user["gender"], user["goal_type"], user["goal_weight"], age)

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM workout_logs
                    WHERE user_id=%s AND logged_at >= NOW() - INTERVAL '7 days'
                """, (user_id,))
                workouts = cur.fetchone()["cnt"]

                cur.execute("""
                    SELECT DATE(logged_at) as day, SUM(calories) as total
                    FROM food_logs
                    WHERE user_id=%s AND logged_at >= NOW() - INTERVAL '7 days'
                    GROUP BY DATE(logged_at)
                """, (user_id,))
                rows = cur.fetchall()
                good_days = sum(1 for r in rows if abs(r["total"] - target) <= 300)

        messages = []
        if workouts < 3:
            messages.append(random.choice(WORKOUT_ROASTS).format(workouts))
        if good_days < 4:
            messages.append(random.choice(NUTRITION_ROASTS).format(good_days))

        if not messages:
            text = (
                f"📊 *Итог недели*\n\n"
                f"🏋️ Тренировок: {workouts}/3 — красава!\n"
                f"🥗 Дней в норме: {good_days}/7 — огонь!\n\n"
                f"💪 Так держать, всё идёт по плану!"
            )
        else:
            text = f"📊 *Итог недели*\n\n" + "\n\n".join(messages)

        await bot.send_message(user_id, text, parse_mode="Markdown")

    except Exception as e:
        logger.warning(f"Cannot send weekly roast to {user_id}: {e}")
