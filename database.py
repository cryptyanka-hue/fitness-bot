import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     BIGINT PRIMARY KEY,
                username    TEXT,
                gender      TEXT,
                height      REAL,
                weight      REAL,
                goal_weight REAL,
                goal_type   TEXT,
                notify_time TEXT DEFAULT '21:00',
                age         INTEGER DEFAULT NULL,
                created_at  TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS food_logs (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                description TEXT,
                calories    REAL,
                protein     REAL,
                fat         REAL,
                carbs       REAL,
                logged_at   TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS workout_logs (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                note        TEXT,
                logged_at   TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS water_logs (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                amount      REAL,
                note        TEXT,
                logged_at   TIMESTAMP DEFAULT NOW()
            );
            """)
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER DEFAULT NULL;")
        conn.commit()


def upsert_user(user_id, username, **fields):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE user_id=%s", (user_id,))
            exists = cur.fetchone()
            if exists:
                if fields:
                    sets = ", ".join(f"{k}=%s" for k in fields)
                    cur.execute(f"UPDATE users SET {sets} WHERE user_id=%s", (*fields.values(), user_id))
            else:
                cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
                if fields:
                    sets = ", ".join(f"{k}=%s" for k in fields)
                    cur.execute(f"UPDATE users SET {sets} WHERE user_id=%s", (*fields.values(), user_id))
        conn.commit()


def get_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            return cur.fetchone()


def add_food_log(user_id, description, calories, protein, fat, carbs):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO food_logs (user_id, description, calories, protein, fat, carbs) VALUES (%s,%s,%s,%s,%s,%s)",
                (user_id, description, calories, protein, fat, carbs)
            )
        conn.commit()


def add_workout_log(user_id, note=""):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO workout_logs (user_id, note) VALUES (%s,%s)", (user_id, note))
        conn.commit()


def add_water_log(user_id, amount, note=""):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO water_logs (user_id, amount, note) VALUES (%s,%s,%s)", (user_id, amount, note))
        conn.commit()


def get_today_food(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM food_logs
                WHERE user_id=%s AND logged_at::date = CURRENT_DATE
            """, (user_id,))
            return cur.fetchall()


def get_today_water(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) as total FROM water_logs
                WHERE user_id=%s AND logged_at::date = CURRENT_DATE
            """, (user_id,))
            return cur.fetchone()["total"]


def get_today_workouts(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM workout_logs
                WHERE user_id=%s AND logged_at::date = CURRENT_DATE
            """, (user_id,))
            return cur.fetchone()["cnt"]


def get_week_workouts(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM workout_logs
                WHERE user_id=%s AND logged_at >= NOW() - INTERVAL '7 days'
            """, (user_id,))
            return cur.fetchone()["cnt"]


def get_all_users():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users")
            return cur.fetchall()


def get_users_without_age():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE age IS NULL AND gender IS NOT NULL")
            return cur.fetchall()


init_db()
