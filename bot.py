"""
Работает с этими модулями:
python-telegram-bot==13.15
redis==3.2.1
"""
import logging
import os

import redis
import requests
from io import BytesIO
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
    strapi_url = 'http://localhost:1337/api'
    headers = {
        'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}'
    }
    products = requests.get(
        os.path.join(strapi_url, 'products'),
        headers=headers,
    ).json()
    keyboard = [
        [InlineKeyboardButton(
            product['attributes']['title'],
            callback_data=product['id'],
        )] for product in products['data']
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def get_menu(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния HANDLE_DESCRIPTION.
    Бот выдает все товары в виде инлайн кнопок.
    Оставляет пользователя в состоянии HANDLE_MENU.
    """
    strapi_url = 'http://localhost:1337/api'
    headers = {
        'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}'
    }
    products = requests.get(
        os.path.join(strapi_url, 'products'),
        headers=headers,
    ).json()
    keyboard = [
        [InlineKeyboardButton(
            product['attributes']['title'],
            callback_data=product['id'],
        )] for product in products['data']
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        update.callback_query.from_user.id,
        'Please choose:',
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def get_description(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния HANDLE_MENU.
    Бот присылает пользователю описание выбранного товара.
    Оставляет пользователя в состоянии HANDLE_DESCRIPTION.
    """
    product_id = update.callback_query.data
    strapi_url = 'http://localhost:1337'
    headers = {
        'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}',
    }
    payload = {'populate': 'picture'}
    product_attributes = requests.get(
        os.path.join(strapi_url, 'api', 'products', product_id),
        headers=headers,
        params=payload,
    ).json()['data']['attributes']
    description = product_attributes['description']

    picture_attributes = product_attributes['picture']['data']['attributes']
    picture_url = os.path.join(strapi_url, picture_attributes['url'][1:])
    dowloaded_picture = BytesIO(requests.get(picture_url).content)

    update.callback_query.delete_message()
    context.bot.send_photo(
        update.callback_query.from_user.id,
        dowloaded_picture,
        caption=description,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    'Добавить в корзину',
                    callback_data=product_id,
                )],
                [InlineKeyboardButton(
                    'Назад',
                    callback_data='back_to_menu'
                )],
            ],
        )
    )

    return 'HANDLE_DESCRIPTION'


def add_to_cart(update: Update, context: CallbackContext) -> str:
    strapi_url = 'http://localhost:1337/api'
    headers = {
        'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}'
    }
    user_id = update.callback_query.from_user.id
    if update.callback_query.data == 'back_to_menu':
        products = requests.get(
            os.path.join(strapi_url, 'products'),
            headers=headers,
        ).json()
        keyboard = [
            [InlineKeyboardButton(
                product['attributes']['title'],
                callback_data=product['id'],
            )] for product in products['data']
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            user_id,
            'Please choose:',
            reply_markup=reply_markup)
    else:
        cart_filter = {'filters[tg_id][$eq]': {user_id}}
        user_cart = requests.get(
            os.path.join(strapi_url, 'carts'),
            params=cart_filter,
        )
        if not user_cart:
            cart_payload = {'data': {'tg_id': user_id}, }
            requests.post(
                os.path.join(strapi_url, 'carts'),
                json=cart_payload,
            )
        productcart_payload = {
            'data': {
                'cart': user_cart.json()['data'][0]['id'],
                'product': update.callback_query.data,
            }
        }
        requests.post(
            os.path.join(strapi_url, 'product-in-carts'),
            json=productcart_payload,
        )
    return "HANDLE_MENU"


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
        'HANDLE_MENU': get_description,
        'HANDLE_DESCRIPTION': add_to_cart,
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
