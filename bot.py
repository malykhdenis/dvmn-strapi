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
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      KeyboardButton, ReplyKeyboardMarkup, Update)
from telegram.ext import (Filters, Updater, CallbackQueryHandler,
                          CommandHandler, MessageHandler, CallbackContext)

_database = None

STRAPI_API_URL = os.getenv('STRAPI_API_URL')
AUTH_HEADER = {'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}', }


def start(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния START.
    Бот отвечает пользователю фразой "Привет!" и переводит его в состояние
    HANDLE_MENU.
    Теперь в ответ на его команды будет запускаеться хэндлер get_description.
    """
    context.bot_data['telegram_id'] = update.message.from_user.id

    update.message.reply_text(
        text='Привет!',
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton('Моя корзина')]]),
    )
    return get_menu(update, context)


def get_menu(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния HANDLE_DESCRIPTION.
    Бот выдает все товары в виде инлайн кнопок.
    Оставляет пользователя в состоянии HANDLE_MENU.
    """
    products = requests.get(
        os.path.join(STRAPI_API_URL, 'products'),
        headers=AUTH_HEADER,
    )
    products.raise_for_status()

    keyboard = [
        [InlineKeyboardButton(
            product['attributes']['title'],
            callback_data=product['id'],
        )] for product in products.json()['data']
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        context.bot_data['telegram_id'],
        'Please choose:',
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def get_description(update: Update, context: CallbackContext) -> str:
    """
    Хэндлер для состояния HANDLE_MENU.
    Бот присылает пользователю описание выбранного товара.
    Оставляет пользователя в состоянии HANDLE_DESCRIPTION.
    """
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context)
        return 'HANDLE_MENU'
    elif update.callback_query.data == 'show_cart':
        show_cart(update, context)
        return 'HANDLE_CART'
    elif update.callback_query.data == 'pay':
        context.bot.send_message(
            update.callback_query.from_user.id,
            'Введите email',
        )
        return 'WAITING_EMAIL'

    product_id = update.callback_query.data
    context.bot_data['product_id'] = product_id

    payload = {'populate': 'picture'}
    product = requests.get(
        os.path.join(STRAPI_API_URL, 'products', product_id),
        headers=AUTH_HEADER,
        params=payload,
    )
    product.raise_for_status()

    product_attributes = product.json()['data']['attributes']
    description = product_attributes['description']
    picture_attributes = product_attributes['picture']['data']['attributes']
    picture_url = os.path.join(
        STRAPI_API_URL[:-4],
        picture_attributes['url'][1:],
    )
    dowloaded_picture = BytesIO(requests.get(picture_url).content)

    update.callback_query.delete_message()
    context.bot.send_photo(
        update.callback_query.from_user.id,
        dowloaded_picture,
        caption=description,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    str(i),
                    callback_data=i,
                ) for i in range(5, 16, 5)],
                [InlineKeyboardButton(
                    'Моя корзина',
                    callback_data='show_cart',
                )],
                [InlineKeyboardButton(
                    'Назад',
                    callback_data='back_to_menu',
                )],
            ],
        )
    )

    return 'HANDLE_DESCRIPTION'


def add_to_cart(update: Update, context: CallbackContext) -> str:
    """Добавить товар в корзину."""
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context)
        return 'HANDLE_MENU'
    elif update.callback_query.data == 'show_cart':
        show_cart(update, context)
        return 'HANDLE_CART'
    elif update.callback_query.data == 'pay':
        context.bot.send_message(
            update.callback_query.from_user.id,
            'Введите email',
        )
        return 'WAITING_EMAIL'
    else:
        cart_filter = {
            'filters[tg_id][$eq]': {context.bot_data['telegram_id']},
        }
        user_cart = requests.get(
            os.path.join(STRAPI_API_URL, 'carts'),
            headers=AUTH_HEADER,
            params=cart_filter,
        )
        user_cart.raise_for_status()

        if not user_cart:
            cart_payload = {
                'data': {'tg_id': {context.bot_data['telegram_id']}},
            }
            create_cart = requests.post(
                os.path.join(STRAPI_API_URL, 'carts'),
                headers=AUTH_HEADER,
                json=cart_payload,
            )
            create_cart.raise_for_status()

        productcart_payload = {
            'data': {
                'cart': user_cart.json()['data'][0]['id'],
                'product': context.bot_data['product_id'],
                'amount': int(update.callback_query.data),
            }
        }
        add_product = requests.post(
            os.path.join(STRAPI_API_URL, 'product-in-carts'),
            headers=AUTH_HEADER,
            json=productcart_payload,
        )
        add_product.raise_for_status()
    return "HANDLE_MENU"


def show_cart(update: Update, context: CallbackContext) -> str:
    """Показать корзину."""
    cart_filter = {
        'filters[tg_id][$eq]': context.bot_data['telegram_id'],
        'populate[cartproducts][populate]': 'product',
    }
    user_cart = requests.get(
        os.path.join(STRAPI_API_URL, 'carts'),
        params=cart_filter,
    )
    user_cart.raise_for_status()

    user_cart_data = user_cart.json()['data'][0]
    context.bot_data['cart_id'] = user_cart_data['id']
    cartproducts = user_cart_data['attributes']['cartproducts']['data']
    total = 0
    cart_text = ''
    inline_keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data='pay')],
        [InlineKeyboardButton('В меню', callback_data='back_to_menu')],
    ]
    for cartproduct in cartproducts:
        product_data = cartproduct['attributes']['product']['data']
        product_id = product_data['id']
        product_title = product_data['attributes']['title']
        product_description = product_data['attributes']['description']
        product_price = product_data['attributes']['price']
        product_amount = cartproduct['attributes']['amount']
        product_total = product_price * product_amount
        total += product_total
        cart_text += (
            f'{product_title}\n'
            f'{product_description}\n'
            f'{product_price:.2f}rub per kg\n'
            f'{product_amount}kg in cart for {product_total:.2f}rub\n\n'
        )
        inline_keyboard.append(
            [InlineKeyboardButton(
                f'Убрать {product_title}', callback_data=product_id,
            )]
        )
    cart_text += f'Total: {total:.2f}rub'
    context.bot.send_message(
        context.bot_data['telegram_id'],
        cart_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard),
    )
    return 'HANDLE_CART'


def handle_cart(update: Update, context: CallbackContext) -> str:
    """Удалить товар из корзины, либо вернуться к списку товаров."""
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context)
        return 'HANDLE_MENU'
    elif update.callback_query.data == 'pay':
        context.bot.send_message(
            update.callback_query.from_user.id,
            'Введите email',
        )
        return 'WAITING_EMAIL'
    else:
        cart_filter = {'filters[tg_id][$eq]': context.bot_data['telegram_id']}
        user_cart = requests.get(
            os.path.join(STRAPI_API_URL, 'carts'),
            headers=AUTH_HEADER,
            params=cart_filter,
        )
        user_cart.raise_for_status()

        user_cart_id = user_cart.json()['data'][0]['id']
        cartproduct_filter = {
            'filters[cart][$eq]': user_cart_id,
            'filters[product][$eq]': update.callback_query.data,
        }
        cartproduct = requests.get(
            os.path.join(STRAPI_API_URL, 'product-in-carts'),
            headers=AUTH_HEADER,
            params=cartproduct_filter,
        )
        cartproduct.raise_for_status()

        cartproduct_id = cartproduct.json()['data'][0]['id']
        delete_product = requests.delete(
            os.path.join(
                STRAPI_API_URL,
                'product-in-carts',
                str(cartproduct_id),
            ),
            headers=AUTH_HEADER,
        )
        delete_product.raise_for_status()

        update.callback_query.delete_message()
        show_cart(update, context)
    return 'HANDLE_CART'


def get_email(update: Update, context: CallbackContext) -> str:
    """Записать email пользователя."""
    user_filter = {'filters[cart][$eq]': context.bot_data['cart_id']}
    user = requests.get(
        os.path.join(STRAPI_API_URL, 'users'),
        headers=AUTH_HEADER,
        params=user_filter,
    )
    user.raise_for_status()

    user_id = user.json()[0]['id']
    payload = {'email': update.message.text}
    update_response = requests.put(
        os.path.join(STRAPI_API_URL, 'users', str(user_id)),
        headers=AUTH_HEADER,
        json=payload,
    )
    try:
        update_response.raise_for_status()
    except Exception:
        update.message.reply_text('Введите валидный email')
        return 'WAITING_EMAIL'
    return 'START'


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
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': get_email,
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
    dispatcher.add_handler(
        MessageHandler(Filters.regex(r'Моя корзина'), show_cart),
    )
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
