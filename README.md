# Твой ангел-хранитель — Telegram-бот

MVP: раз в день в случайное время (09:00–21:00) присылает подписчику одну короткую поддерживающую фразу.

## Шаг 1. Создать бота в Telegram

1. Открой Telegram, найди **@BotFather**.
2. Напиши `/newbot`, следуй инструкциям: имя — «Твой ангел-хранитель», username — что-то вроде `tvoy_angel_hranitel_bot`.
3. BotFather пришлёт токен вида `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
4. (Опционально) пришли BotFather команду `/setuserpic` и загрузи аватар бота.

## Шаг 2. Настроить проект

```bash
cd /home/Natali/angel-bot
cp .env.example .env
```

Открой `.env` и вставь свой токен вместо заглушки.

## Шаг 3. Установить зависимости и запустить

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
python3 bot.py
```

(`--break-system-packages` нужен, потому что система защищает системный Python от установки пакетов напрямую — это ставит их в твою личную папку, ничего не ломает).

В терминале появится `Бот запущен...`. Открой своего бота в Telegram и нажми **Start** — бот подпишет тебя и подтвердит это сообщением.

Команда `/now` — присылает тестовую фразу сразу, не дожидаясь ежедневной рассылки (удобно для проверки).
Команда `/stop` — отписка.

## Шаг 4. Деплой на бесплатный хостинг (чтобы бот работал 24/7)

Локально бот работает, только пока запущен `python3 bot.py` на твоём компьютере. Чтобы он слал сообщения даже когда компьютер выключен — задеплой на Render.com (Background Worker, free tier) или Railway.app:

1. Залей папку `angel-bot` в приватный репозиторий на GitHub.
2. На Render.com: New → Background Worker → подключи репозиторий.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. В Environment Variables добавь `BOT_TOKEN` со своим значением.

## Файлы проекта

- `bot.py` — логика бота и расписание рассылки
- `phrases.json` — банк фраз по категориям (легко редактировать/дополнять)
- `database.py` — хранение подписчиков (SQLite, файл `subscribers.db` создастся автоматически)
