import json
import os
import random
from datetime import datetime, timedelta

import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN — добавь его в файл .env")

SENDER_NAME = "Твой ангел-хранитель"
SEND_WINDOW_START_HOUR = 9
SEND_WINDOW_END_HOUR = 21

bot = telebot.TeleBot(TOKEN)
db.init_db()

with open("phrases.json", "r", encoding="utf-8") as f:
    _categories = json.load(f)
PHRASES = [text for texts in _categories.values() for text in texts]


def pick_phrase(last_index: int) -> tuple[str, int]:
    if len(PHRASES) == 1:
        return PHRASES[0], 0
    index = last_index
    while index == last_index:
        index = random.randrange(len(PHRASES))
    return PHRASES[index], index


@bot.message_handler(commands=["start"])
def handle_start(message):
    db.add_subscriber(message.chat.id, message.from_user.first_name or "")
    bot.send_message(
        message.chat.id,
        f"Здравствуй. Я — {SENDER_NAME}.\n\n"
        "Я буду присылать тебе одно короткое послание раз в день — "
        "в случайное время, чтобы оно находило тебя тогда, когда действительно нужно.\n\n"
        "Чтобы остановить рассылку — просто напиши /stop.",
    )


@bot.message_handler(commands=["stop"])
def handle_stop(message):
    db.remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "Хорошо. Ты можешь вернуться в любой момент, написав /start.")


@bot.message_handler(commands=["now"])
def handle_now(message):
    """Тестовая отправка одной фразы прямо сейчас — удобно для проверки, что бот жив."""
    phrase, _ = pick_phrase(-1)
    bot.send_message(message.chat.id, phrase)


def broadcast_daily_phrase():
    for chat_id, _name in db.get_all_subscribers():
        conn = db.sqlite3.connect(db.DB_PATH)
        row = conn.execute(
            "SELECT last_phrase_index FROM subscribers WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        conn.close()
        last_index = row[0] if row else -1

        phrase, new_index = pick_phrase(last_index)
        try:
            bot.send_message(chat_id, phrase)
            conn = db.sqlite3.connect(db.DB_PATH)
            conn.execute(
                "UPDATE subscribers SET last_phrase_index = ? WHERE chat_id = ?",
                (new_index, chat_id),
            )
            conn.commit()
            conn.close()
        except telebot.apihelper.ApiException:
            db.remove_subscriber(chat_id)


def schedule_todays_broadcast(scheduler: BackgroundScheduler):
    now = datetime.now()
    window_start = now.replace(hour=SEND_WINDOW_START_HOUR, minute=0, second=0, microsecond=0)
    window_end = now.replace(hour=SEND_WINDOW_END_HOUR, minute=0, second=0, microsecond=0)

    earliest = max(now + timedelta(minutes=1), window_start)
    if earliest >= window_end:
        return

    delta_seconds = int((window_end - earliest).total_seconds())
    send_time = earliest + timedelta(seconds=random.randint(0, delta_seconds))
    scheduler.add_job(broadcast_daily_phrase, "date", run_date=send_time)
    print(f"Сегодняшняя рассылка запланирована на {send_time.strftime('%H:%M:%S')}")


def schedule_next_day_planner(scheduler: BackgroundScheduler):
    scheduler.add_job(
        lambda: schedule_todays_broadcast(scheduler),
        "cron",
        hour=0,
        minute=5,
    )


if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    schedule_todays_broadcast(scheduler)
    schedule_next_day_planner(scheduler)
    scheduler.start()

    print(f"Бот запущен. Фраз в базе: {len(PHRASES)}. Подписчиков: {db.count_subscribers()}")
    bot.infinity_polling()
