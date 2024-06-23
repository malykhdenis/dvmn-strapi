# dvmn-strapi

## Описание
Telegram бот для интернет магазина морепродуктов.

## Установка и запуск

### Клонирование репозитория

Клонируйте репозиторий командой в терминале:
```bash
git clone https://github.com/malykhdenis/dvmn-strapi.git
```

### Создание виртуального окружения

Создайте виртуальное окружение командой:
```bash
pyhton -m venv venv
```

### Установка зависимостей

Установите зависимости из файла `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Создание файла `.env` с переменными окружения

Создайте файл `.env` и поместите в него следующие переменные окружения:
```
TELEGRAM_BOT_TOKEN="Токен бота в Telegram"
STRAPI_TOKEN="Токен авторизации сервиса Strapi"
STRAPI_API_URL="URL адрес API сервиса Strapi" (локальный 'http://localhost:1337/api')
REDIS_HOST="Адрес базы данных"
REDIS_PORT="Порт базы данных"
REDIS_PASSWORD="Пароль для доступа к базе данных"
```
Для создания базы данных Reddis - https://redislabs.com

Для создания проекта в Strapi и получения токена авторизации - https://github.com/strapi/strapi

### bot.py

Запустите Telegram бот командой в терминале:
```bash
python telegram_bot.py
```
