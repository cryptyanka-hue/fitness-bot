import os

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
GROQ_KEY   = os.environ.get("GROQ_KEY", "")
DATABASE   = os.environ.get("DATABASE", "fitness.db")
ADMIN_IDS  = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
