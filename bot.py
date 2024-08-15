import logging
import os
from functools import partial

import redis
from dotenv import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      KeyboardButton, ReplyKeyboardMarkup, Update)
from telegram.ext import (Filters, Updater, CallbackQueryHandler,
                          CommandHandler, MessageHandler, CallbackContext)

from strapi_requests import (add_product, create_cart, delete_cartproduct,
                             download_picture, get_cart, get_cartproduct,
                             get_product_with_picture, get_products,
                             get_user, save_email)

_database = None

WEIGHTS = [5, 10, 15]


def start(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
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
    return get_menu(update, context, strapi_token, strapi_api_url)


def get_menu(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """
    Хэндлер для состояния HANDLE_DESCRIPTION.
    Бот выдает все товары в виде инлайн кнопок.
    Оставляет пользователя в состоянии HANDLE_MENU.
    """
    products = get_products(strapi_token, strapi_api_url)
    keyboard = [
        [InlineKeyboardButton(
            product['attributes']['title'],
            callback_data=product['id'],
        )] for product in products['data']
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        context.bot_data['telegram_id'],
        'Please choose:',
        reply_markup=reply_markup)
    return 'HANDLE_MENU'


def get_description(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """
    Хэндлер для состояния HANDLE_MENU.
    Бот присылает пользователю описание выбранного товара.
    Оставляет пользователя в состоянии HANDLE_DESCRIPTION.
    """
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context, strapi_token, strapi_api_url)
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

    product = get_product_with_picture(
        product_id,
        strapi_token,
        strapi_api_url,
    )

    product_attributes = product['data']['attributes']
    description = product_attributes['description']
    picture_attributes = product_attributes['picture']['data']['attributes']
    picture_url = picture_attributes['url'][1:]

    dowloaded_picture = download_picture(picture_url, strapi_api_url)

    context.bot.send_photo(
        update.callback_query.from_user.id,
        dowloaded_picture,
        caption=description,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    str(i),
                    callback_data=i,
                ) for i in WEIGHTS],
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
    update.callback_query.delete_message()

    return 'HANDLE_DESCRIPTION'


def add_to_cart(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """Добавить товар в корзину."""
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context, strapi_token, strapi_api_url)
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
        telegram_id = context.bot_data['telegram_id']

        user_cart = get_cart(telegram_id, strapi_token, strapi_api_url)

        if not user_cart:
            create_cart(telegram_id, strapi_token, strapi_api_url)
            user_cart = get_cart(telegram_id, strapi_token, strapi_api_url)

        cart_id = user_cart['data'][0]['id']
        product_id = context.bot_data['product_id']
        amount = int(update.callback_query.data)
        add_product(cart_id, product_id, amount, strapi_token, strapi_api_url)
    return "HANDLE_MENU"


def show_cart(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """Показать корзину."""
    telegram_id = context.bot_data['telegram_id']
    user_cart = get_cart(
        telegram_id,
        strapi_token,
        strapi_api_url,
    )

    user_cart_data = user_cart['data'][0]
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


def handle_cart(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """Удалить товар из корзины, либо вернуться к списку товаров."""
    if update.callback_query.data == 'back_to_menu':
        get_menu(update, context, strapi_token, strapi_api_url)
        return 'HANDLE_MENU'
    elif update.callback_query.data == 'pay':
        context.bot.send_message(
            update.callback_query.from_user.id,
            'Введите email',
        )
        return 'WAITING_EMAIL'
    else:
        telegram_id = context.bot_data['telegram_id']
        user_cart = get_cart(telegram_id, strapi_token, strapi_api_url)

        user_cart_id = user_cart['data'][0]['id']
        product_id = update.callback_query.data
        cartproduct = get_cartproduct(
            user_cart_id,
            product_id,
            strapi_token,
            strapi_api_url,
        )

        cartproduct_id = cartproduct['data'][0]['id']
        delete_cartproduct(cartproduct_id, strapi_token, strapi_api_url)

        show_cart(update, context)
        update.callback_query.delete_message()
    return 'HANDLE_CART'


def get_email(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> str:
    """Записать email пользователя."""
    cart_id = context.bot_data['cart_id']
    user = get_user(cart_id, strapi_token, strapi_api_url)

    user_id = user[0]['id']
    email = update.message.text
    try:
        save_email(user_id, email, strapi_token, strapi_api_url)
    except Exception:
        update.message.reply_text('Введите валидный email')
        return 'WAITING_EMAIL'
    return 'START'


def handle_users_reply(
        update: Update,
        context: CallbackContext,
        strapi_token: str,
        strapi_api_url: str) -> None:
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
        next_state = state_handler(
            update,
            context,
            strapi_token,
            strapi_api_url,
        )
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


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    load_dotenv()
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    strapi_token = os.getenv("STRAPI_TOKEN")
    strapi_api_url = os.getenv('STRAPI_API_URL')
    updater = Updater(telegram_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(r'Моя корзина'),
            partial(
                show_cart,
                strapi_token=strapi_token,
                strapi_api_url=strapi_api_url,
            ),
        ),
    )
    handle_users_reply_partial = partial(
        handle_users_reply,
        strapi_token=strapi_token,
        strapi_api_url=strapi_api_url,
    )
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_partial))
    dispatcher.add_handler(
        MessageHandler(Filters.text, handle_users_reply_partial)
    )
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_partial))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
