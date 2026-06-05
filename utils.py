import aiohttp
import json
from config import GROQ_KEY


def calc_bmi(weight: float, height_cm: float) -> float:
    h = height_cm / 100
    return weight / (h * h)


def bmi_verdict(bmi: float, gender: str) -> str:
    if bmi < 16:
        return "⚠️ Выраженный дефицит массы тела"
    elif bmi < 18.5:
        return "⚠️ Дефицит массы тела — тебе нужно набрать вес!"
    elif bmi < 25:
        return "✅ Нормальная масса тела"
    elif bmi < 30:
        return "⚠️ Избыточная масса тела"
    elif bmi < 35:
        return "🔴 Ожирение I степени"
    else:
        return "🔴 Ожирение II+ степени"


def calc_calories(weight: float, height: float, gender: str, goal_type: str, goal_weight: float, age: int = 30) -> int:
    if gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = bmr * 1.375
    if goal_type in ("похудеть", "снизить процент жира"):
        return int(tdee - 400)
    elif goal_type in ("набрать мышечную массу", "набрать общий вес"):
        return int(tdee + 300)
    else:
        return int(tdee)


async def _groq_request(prompt: str) -> str | None:
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 100,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                raw = await resp.text()
                data = json.loads(raw)
                if "error" in data:
                    print(f"Groq error: {data['error']}")
                    return None
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return None


async def parse_food_with_ai(description: str) -> dict | None:
    prompt = (
        f"Пользователь съел: \"{description}\"\n\n"
        "Оцени КБЖУ (калории, белки, жиры, углеводы).\n"
        "Ответь ТОЛЬКО JSON без markdown:\n"
        "{\"calories\": 350, \"protein\": 12.5, \"fat\": 8.0, \"carbs\": 55.0}"
    )
    text = await _groq_request(prompt)
    if not text:
        return None
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Food parse error: {e}")
        return None


async def parse_water_with_ai(description: str) -> dict | None:
    prompt = (
        f"Пользователь выпил: \"{description}\"\n\n"
        "Определи объём жидкости в литрах и название напитка если указано.\n"
        "Ответь ТОЛЬКО JSON без markdown:\n"
        "{\"amount\": 0.5, \"note\": \"вода\"}\n"
        "Если напиток не указан — note пустая строка.\n"
        "Примеры: '0.5' -> {\"amount\": 0.5, \"note\": \"\"}, "
        "'стакан воды' -> {\"amount\": 0.25, \"note\": \"вода\"}, "
        "'банка колы 0.33' -> {\"amount\": 0.33, \"note\": \"кола\"}"
    )
    text = await _groq_request(prompt)
    if not text:
        return None
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Water parse error: {e}")
        return None
