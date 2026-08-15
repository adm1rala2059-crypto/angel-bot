import json
import os
import random
import time
from datetime import date, datetime, timedelta

import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from telebot import types

import database as db
from keepalive import start_keepalive_server

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN — добавь его в файл .env")

SENDER_NAME = "Твой ангел-хранитель"
SEND_WINDOW_START_HOUR = 9
SEND_WINDOW_END_HOUR = 21
QUESTION_PROBABILITY = 0.25
REENGAGEMENT_AFTER_DAYS = 3
REENGAGEMENT_REPEAT_AFTER_DAYS = 4

bot = telebot.TeleBot(TOKEN)
db.init_db()

with open("phrases.json", "r", encoding="utf-8") as f:
    _categories = json.load(f)
PHRASES = [text for texts in _categories.values() for text in texts]

with open("gifts.json", "r", encoding="utf-8") as f:
    GIFTS = json.load(f)

with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

with open("reengagement.json", "r", encoding="utf-8") as f:
    REENGAGEMENT_MESSAGES = json.load(f)


def pick_from(pool: list[str], last_index: int) -> tuple[str, int]:
    if len(pool) == 1:
        return pool[0], 0
    index = last_index
    while index == last_index:
        index = random.randrange(len(pool))
    return pool[index], index


def pick_phrase(last_index: int) -> tuple[str, int]:
    return pick_from(PHRASES, last_index)


def pick_gift(last_index: int) -> tuple[str, int]:
    return pick_from(GIFTS, last_index)


def accept_keyboard() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🙏 Принимаю", callback_data="accept"))
    return markup


@bot.message_handler(commands=["start"])
def handle_start(message):
    db.add_subscriber(message.chat.id, message.from_user.first_name or "")
    bot.send_message(
        message.chat.id,
        f"Привет, милая 🤍 Я — {SENDER_NAME}, и теперь я всегда рядом.\n\n"
        "Раз в день, в случайный момент, буду прилетать к тебе с тёплым словом 🕊️ "
        "— именно тогда, когда оно нужнее всего.\n\n"
        "А если однажды захочется тишины — напиши /stop, я пойму",
    )


@bot.message_handler(commands=["stop"])
def handle_stop(message):
    db.remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "Хорошо. Ты можешь вернуться в любой момент, написав /start.")


def send_and_log(chat_id: int, text: str, message_type: str):
    msg = bot.send_message(chat_id, text, reply_markup=accept_keyboard())
    db.log_event(chat_id, msg.message_id, message_type, text, datetime.now().isoformat())
    return msg


@bot.message_handler(commands=["now"])
def handle_now(message):
    """Тестовая отправка одной фразы прямо сейчас — удобно для проверки, что бот жив."""
    phrase, _ = pick_phrase(-1)
    send_and_log(message.chat.id, phrase, "test")


@bot.callback_query_handler(func=lambda call: call.data == "accept")
def handle_accept(call):
    bot.answer_callback_query(call.id, "💛")
    bot.edit_message_text(
        call.message.text + "\n\n✅ Принято",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )
    db.mark_event_accepted(call.message.chat.id, call.message.message_id, datetime.now().isoformat())

    _, last_gift_index = db.get_indices(call.message.chat.id)
    gift, new_gift_index = pick_gift(last_gift_index)
    db.set_last_gift_index(call.message.chat.id, new_gift_index)

    today = date.today()
    streak = db.record_accept(
        call.message.chat.id, today.isoformat(), (today - timedelta(days=1)).isoformat()
    )
    streak_line = ""
    if streak > 1:
        word = "день" if streak % 10 == 1 and streak % 100 != 11 else "дня" if 2 <= streak % 10 <= 4 and not 12 <= streak % 100 <= 14 else "дней"
        streak_line = f"\n\n🔥 Серия: {streak} {word} подряд"

    bot.send_message(call.message.chat.id, f"🎁 Подарок за отклик:\n{gift}{streak_line}")


def should_reengage(last_accept_date: str | None, last_reengagement_date: str | None, today: date) -> bool:
    reference_date = last_accept_date or last_reengagement_date
    if reference_date is None:
        return False  # новый подписчик, ещё рано напоминать

    days_quiet = (today - date.fromisoformat(reference_date)).days
    if last_accept_date is None:
        return days_quiet >= REENGAGEMENT_AFTER_DAYS

    if days_quiet < REENGAGEMENT_AFTER_DAYS:
        return False

    if last_reengagement_date is None:
        return True

    days_since_last_nudge = (today - date.fromisoformat(last_reengagement_date)).days
    return days_since_last_nudge >= REENGAGEMENT_REPEAT_AFTER_DAYS


def broadcast_daily_phrase():
    today = date.today()
    for chat_id, _name in db.get_all_subscribers():
        last_accept_date, _, last_reengagement_date = db.get_engagement(chat_id)

        try:
            if should_reengage(last_accept_date, last_reengagement_date, today):
                text = random.choice(REENGAGEMENT_MESSAGES)
                send_and_log(chat_id, text, "reengagement")
                db.set_last_reengagement_date(chat_id, today.isoformat())
            elif random.random() < QUESTION_PROBABILITY:
                text = random.choice(QUESTIONS)
                send_and_log(chat_id, text, "question")
            else:
                last_index, _ = db.get_indices(chat_id)
                phrase, new_index = pick_phrase(last_index)
                send_and_log(chat_id, phrase, "phrase")
                db.set_last_phrase_index(chat_id, new_index)
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
    start_keepalive_server()

    scheduler = BackgroundScheduler()
    schedule_todays_broadcast(scheduler)
    schedule_next_day_planner(scheduler)
    scheduler.start()

    print(f"Бот запущен. Фраз в базе: {len(PHRASES)}. Подписчиков: {db.count_subscribers()}")

    # infinity_polling может упасть целиком (например, на 409 Conflict, если на
    # секунду пересеклись два инстанса при деплое) — процесс не должен из-за
    # этого умирать насовсем, поэтому оборачиваем в собственный цикл перезапуска.
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Polling упал с ошибкой: {e}. Перезапуск через 5 секунд...")
            time.sleep(5)
