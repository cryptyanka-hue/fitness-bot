import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ConversationHandler
)
from onboarding import (
    start, get_gender, get_height, get_weight,
    get_goal_weight, get_goal_type, get_notify_time, get_age,
    ask_age_existing, save_age_existing,
    GENDER, HEIGHT, WEIGHT, GOAL_WEIGHT, GOAL_TYPE, NOTIFY_TIME, AGE
)
from tracking import (
    log_food, log_workout, log_water, show_profile,
    handle_buttons, waiting_food_input, waiting_water_input
)
from admin import broadcast
from scheduler import setup_scheduler, ask_age_for_users
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BUTTON_TEXTS = filters.Regex("^(🍽 Добавить еду|💧 Вода|💪 Тренировка|📊 Мой профиль)$")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GENDER:      [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_gender)],
            HEIGHT:      [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_height)],
            WEIGHT:      [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_weight)],
            GOAL_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_goal_weight)],
            GOAL_TYPE:   [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_goal_type)],
            AGE:         [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_age)],
            NOTIFY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, get_notify_time)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    age_conv = ConversationHandler(
        entry_points=[CommandHandler("setage", ask_age_existing)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, save_age_existing)],
        },
        fallbacks=[],
    )

    food_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🍽 Добавить еду$"), handle_buttons)],
        states={
            waiting_food_input: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, log_food)],
        },
        fallbacks=[],
    )

    water_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💧 Вода$"), handle_buttons)],
        states={
            waiting_water_input: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~BUTTON_TEXTS, log_water)],
        },
        fallbacks=[],
    )

    app.add_handler(onboarding)
    app.add_handler(age_conv)
    app.add_handler(food_conv)
    app.add_handler(water_conv)
    app.add_handler(MessageHandler(filters.Regex("^(💪 Тренировка|📊 Мой профиль)$"), handle_buttons))
    app.add_handler(CommandHandler("log", log_food))
    app.add_handler(CommandHandler("workout", log_workout))
    app.add_handler(CommandHandler("me", show_profile))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.job_queue.run_repeating(setup_scheduler, interval=60, first=10)
    app.job_queue.run_once(ask_age_for_users, when=30)

    logger.info("Bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
