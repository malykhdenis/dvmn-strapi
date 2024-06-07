"""
Работает с этими модулями:
python-telegram-bot==13.15
redis==3.2.1
"""
import logging
import os
import redis

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Filters, Updater, CallbackQueryHandler,
                          CommandHandler, MessageHandler, CallbackContext)

_database = None


def start(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния START.
    Бот отвечает пользователю фразой "Привет!" и переводит его в состояние
    ECHO.
    Теперь в ответ на его команды будет запускаеться хэндлер echo.
    """
    update.message.reply_text(text='Привет!')
    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data='1'),
            InlineKeyboardButton("Option 2", callback_data='2'),
        ],
        [InlineKeyboardButton("Option 3", callback_data='3')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "ECHO"


def echo(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния ECHO.
    Бот отвечает пользователю тем же, что пользователь ему написал.
    Оставляет пользователя в состоянии ECHO.
    """
    if update.callback_query.data:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text=f"Selected option: {query.data}")
    else:
        users_reply = update.message.text
        update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(update: Update, context: CallbackContext) -> None:
    """
    Функция, которая запускается при любом сообщении от пользователя и решает
    как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую
    функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в
    базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его
    написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может
    воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'ECHO': echo
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё
    не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv("REDIS_PASSWORD")
        database_host = os.getenv("REDIS_HOST")
        database_port = os.getenv("REDIS_PORT")
        _database = redis.Redis(
            host=database_host,
            port=database_port,
            password=database_password
        )
    return _database


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
