from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from datetime import datetime, time, timedelta
import pytz
import requests
import gspread
from google.oauth2.service_account import Credentials
import logging  # Добавляем модуль для логирования
import os


# Укажите ваш часовой пояс (например, для Украины это 'Europe/Kiev')
local_tz = pytz.timezone("Europe/Kiev")

# Текущее время с учетом часового пояса
local_time = datetime.now(local_tz)

# Если нужно добавить час (например, если сервер использует UTC, но бот ожидает местное время)
corrected_time = local_time + timedelta(hours=1)

print("Local Time:", local_time.strftime("%Y-%m-%d %H:%M:%S"))
print("Corrected Time:", corrected_time.strftime("%Y-%m-%d %H:%M:%S"))

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определяем этапы диалога
DISTANCE_INPUT = 1


# Обработка ошибок и логирование
def log_error(error_msg):
    logger.error(f"Ошибка: {error_msg}")  # Логируем ошибки


# Функция для запроса расходов
async def request_distance(update, context):
    context.user_data["transport_type"] = "expenses"  # Устанавливаем тип как "expenses"
    logger.info("Запрос транспортных расходов от пользователя")
    await update.callback_query.message.reply_text(
        "Введите транспортные расходы до места назначения в гривне:"
    )
    return DISTANCE_INPUT


# Функция для запроса расстояния
async def request_distance2(update, context):
    context.user_data["transport_type"] = "distance"  # Устанавливаем тип как "distance"
    logger.info("Запрос расстояния от пользователя")
    await update.callback_query.message.reply_text(
        "Введите расстояние до места назначения в км (тариф для расчета 40 грн/км):"
    )
    return DISTANCE_INPUT


def fetch_google_sheet_data(cells):
    try:
        # Получение ключа таблицы из переменных окружения
        key = os.getenv("GOOGLE_SHEET_KEY")
        logger.info(f"GOOGLE_SHEET_KEY: {GOOGLE_SHEET_KEY}")

        # Формирование учетных данных из переменных окружения
        credentials_info = {
            "type": "service_account",
            "project_id": "uah-bot-project",
            "private_key_id": "601aaa7a81b8b55c79f587c1e94d436b2524d065",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQChNTim3RaWoZME\n3iGj1yw86FvrTaTf0ybLwxTEDEXgaZqzs3dqOzs/1Q+EbEw0mFEXPzxLsViY9M8d\npcpmP+NXwKSmon6Uduib6Apudys3IeDKpXl7UMaWW8V3zGXixGSjg0zInwGCEU/e\n9vsOaq8n4knFFSS86bmN9KBy7XWjMFcTwzkNvijiHPtzEepofki9hoGx3axRVGD5\nfJsoIU3aZacOUZzfVZUFejmc58OQ87i9aYTPRpBm/2yoPYeIVfvfXokn+/o5XXit\ns2uwkgdxlwInTWq7bFVCrW/azMiE1yr39W5x1u7JRGRcn1ePvo3mJaC4c/eOzGvt\nE9rI8jIZAgMBAAECggEAARSZfNrR/i/2i4uOl6nHSOA4z36teneQlMCJuNepNzwV\n9prfE8XyW3bq2/Ua3KZhssFwfsRhRuMrKTR1gxJuDGZE5D4GEaorXHIlccCYOE4g\nktMhmY88yYCzdd5Xl3m//+2PG/Ae4zeI/MJUg+/4nRCR9IF0BdUeMoKfea24Ql/7\nlxMZ0YsCQb5u1tK2cysu+U0rfgxjzBZB1Kf1U0CUnOWi/o/KIxpbGmVVT+WnpOWT\nmQiOLBeGUgA1vIAr7lKTkSh6tRk/s/qgoAPnJhxOH+mOAw4FBWrIYO79IakzMrVx\nCZL/i9LU/n+sCGtbYdNVWZqRWgXU0JNTAk2gI4WS4QKBgQDXhnmt1nW1tp3fnh0P\n8W4qgXRnphk4N8LbelbRm29zke20Z/1VeNsn1BqWfX7my4Xg9XO8eGGq5JAveKJZ\nwxxBObK1qnHwPjOr2ISTpWx32mi0Qj1brLcxuzVVrr65YxkevFl8D40xcotx1Mqn\n+sRXUH+jMz13yoqtNrNJ3quScQKBgQC/e2Z0jFQTu6G81H03yLl8zfszarBKcT/5\n0XJwHGmpoaOTiSs4dJ2RCOe/i9TzLepGvhvWPbfs7Oz89DaJtlwIm3HqLLMY2w/N\n6kspC+bq0ctqiNB89E3PCoiHXKwVTfRlr2wWChAlwry3nQWcrg7ySVkVzMrGDLxg\nqOTl63aeKQKBgHcrTup08373K5HyriUbnIt6KvAIolc4VdDfc1PQuy5O2P1wpl31\nRlBechkV6O4aSLtbXJQwh+hjGup0rGgvftb93TefuAJbklyJirzMsg4PQOey3JRt\nCpo/5jyrM5/0EHazNFNpketuZ3YYb7mz6Y5R31FQysMKxeUCot3MdlexAoGAZoDd\noOh6HbIk69voSFOIkDoIDkc/pion8Ejh9QgQvEEOOu2EGI28x6Y3wT9OuPtMXaBp\ncG/LpOZUGzl0dJYNgIIOIijZmyWxuS6CG7AGZo/2T8p7qVhyyrG90pCWgjUf7stQ\nlh++8yfjNHu3RF+dGrCPIu9lYU3yDeB74GUDM7kCgYBjxvndwyM/RhN4Po34cgVa\nOVEL9U03RoOfH+clsHdkaJvp/wQ3fVbrFH+pCmp0TFRR8Zzoo2BHlnww7nfNTGZl\nSLx7r9U5s2okHm0oE92AFLLxGHX9k1GUZFPcb6A/VwIrvIUEmivoylFoOZO1evbF\n5EXBnW9mNw9Km8CdqWm4NQ==\n-----END PRIVATE KEY-----\n",
            "client_email": "google-sheets-access@uah-bot-project.iam.gserviceaccount.com",
            "client_id": "117294692513868440902",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/google-sheets-access%40uah-bot-project.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com",
        }
        logger.info(f"Credentials Info: {credentials_info}")
        # Авторизация в Google API
        creds = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        worksheet = client.open_by_key(key).get_worksheet(0)

        return [worksheet.acell(cell).value for cell in cells]
    except Exception as e:
        log_error(f"Ошибка при работе с Google Sheets: {e}")
        return ["Ошибка"] * len(cells)


def get_prices_usd():
    cells = ["F2", "F3", "F4", "F5", "A3", "A4"]
    prices = fetch_google_sheet_data(cells)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Цены на дизельное топливо (обновлено {now}):\n"
        f"1. Jasło: {prices[0]}$/t\n"
        f"2. Małaszewicze: {prices[1]}$/t\n"
        f"3. Wola: {prices[2]}$/t\n"
        f"4. Radzionków: {prices[3]}$/t\n"
        f"GASOIL {prices[4]} - {prices[5]}$"
    )


def get_prices_uah():
    cells = ["S2", "S3", "S4", "S5", "A3", "A4"]
    prices = fetch_google_sheet_data(cells)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Цены на дизельное топливо (обновлено {now}):\n"
        f"1. Jasło: {prices[0]}грн/л\n"
        f"2. Małaszewicze: {prices[1]}грн/л\n"
        f"3. Wola: {prices[2]}грн/л\n"
        f"4. Radzionków: {prices[3]}грн/л\n"
        f"GASOIL {prices[4]} - {prices[5]}$"
    )


# Получение курса USD к UAH
def get_exchange_rate():
    try:
        response = requests.get(
            "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
        )
        response.raise_for_status()
        data = response.json()
        return data[0]["rate"]
    except Exception as e:
        log_error(f"Ошибка при получении курса валют: {e}")
        return "Ошибка при получении курса."


# Функция для расчета цены с транспортом (упрощенная версия)
async def calculate_price_with_transport(update, context):
    # Получаем расстояние от пользователя
    distance = float(update.message.text.strip())

    # Получаем цену FCA из Google Sheets
    fca_cells = ["S2", "S3", "S4", "S5", "N2", "N3", "N4", "N5"]
    fca_prices = [
        float(price.replace(",", ".").strip())
        for price in fetch_google_sheet_data(fca_cells)
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Рассчитываем стоимость с учетом транспортировки
    message = (
        f"Цены на дизельное топливо с доставкой (запрос в гривнах)(обновлено {now}):\n"
        f"1. Jasło: {(fca_prices[0] + distance * fca_prices[4] * 0.001 / 25):.2f} грн/л\n"
        f"2. Małaszewicze: {(fca_prices[1] + distance * fca_prices[5] * 0.001 / 25):.2f} грн/л\n"
        f"3. Wola: {(fca_prices[2] + distance * fca_prices[6] * 0.001 / 25):.2f} грн/л\n"
        f"4. Radzionków: {(fca_prices[3] + distance * fca_prices[7] * 0.001 / 25):.2f} грн/л\n"
    )

    # Отправляем результат пользователю
    await update.message.reply_text(message)
    return ConversationHandler.END


# Функция для расчета цены с транспортом (упрощенная версия)
async def calculate_price_with_transport2(update, context):
    # Получаем расстояние от пользователя
    distance = float(update.message.text.strip())
    logger.info(f"Пользователь ввел: {distance} км")

    # Получаем цену FCA из Google Sheets
    fca_cells = ["S2", "S3", "S4", "S5", "N2", "N3", "N4", "N5"]
    fca_prices = [
        float(price.replace(",", ".").strip())
        for price in fetch_google_sheet_data(fca_cells)
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Рассчитываем стоимость с учетом транспортировки
    message = (
        f"Цены на дизельное топливо с доставкой (запрос в км))(обновлено {now}):\n"
        f"1. Jasło: {(fca_prices[0] + distance * 40 * 2 * fca_prices[4] * 0.001 / 25):.2f} грн/л\n"
        f"2. Małaszewicze: {(fca_prices[1] + distance * 40 * 2 * fca_prices[5] * 0.001 / 25):.2f} грн/л\n"
        f"3. Wola: {(fca_prices[2] + distance * 40 * 2 * fca_prices[6] * 0.001 / 25):.2f} грн/л\n"
        f"4. Radzionków: {(fca_prices[3] + distance * 40 * 2 * fca_prices[7] * 0.001 / 25):.2f} грн/л\n"
    )

    # Отправляем результат пользователю
    await update.message.reply_text(message)
    return ConversationHandler.END


# Отправка сообщения с кнопками
async def send_message_with_buttons(chat_id, bot, message):
    keyboard = [
        [
            InlineKeyboardButton(
                "Обновить цены в долларах", callback_data="refresh_prices"
            )
        ],
        [
            InlineKeyboardButton(
                "Обновить цены в гривне", callback_data="refresh_prices_UAH"
            )
        ],
        [
            InlineKeyboardButton(
                "Цена с транспортом (затраты)", callback_data="price_with_transport"
            )
        ],
        [
            InlineKeyboardButton(
                "Цена с транспортом (км)", callback_data="price_with_transport2"
            )
        ],
        [
            InlineKeyboardButton(
                "Проверить курс гривны НБУ", callback_data="check_again"
            )
        ],
        [
            InlineKeyboardButton(
                "Перейти на сайт Межбанк онлайн",
                url="https://minfin.com.ua/currency/mb/usd/",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


# Обработчик команды /start с параметром
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = get_prices_usd()

    await send_message_with_buttons(chat_id, context.bot, message)


# Обработчик кнопок
async def button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    if query.data == "check_again":
        rate = get_exchange_rate()
        message = f"Текущий курс USD к UAH: {rate}"
    elif query.data == "refresh_prices":
        message = get_prices_usd()
    elif query.data == "refresh_prices_UAH":
        message = get_prices_uah()
    elif query.data == "price_with_transport":
        # Явно устанавливаем контекст для первого сценария
        context.user_data["transport_type"] = "expenses"
        await request_distance(update, context)
        return DISTANCE_INPUT
    elif query.data == "price_with_transport2":
        # Явно устанавливаем контекст для второго сценария
        context.user_data["transport_type"] = "distance"
        await request_distance2(update, context)
        return DISTANCE_INPUT
    else:
        message = "Неизвестная команда."

    # Обновляем текст сообщения и кнопки
    keyboard = [
        [
            InlineKeyboardButton(
                "Обновить цены в долларах", callback_data="refresh_prices"
            )
        ],
        [
            InlineKeyboardButton(
                "Обновить цены в гривне", callback_data="refresh_prices_UAH"
            )
        ],
        [
            InlineKeyboardButton(
                "Цена с транспортом (затраты)", callback_data="price_with_transport"
            )
        ],
        [
            InlineKeyboardButton(
                "Цена с транспортом (км)", callback_data="price_with_transport2"
            )
        ],
        [
            InlineKeyboardButton(
                "Проверить курс гривны НБУ", callback_data="check_again"
            )
        ],
        [
            InlineKeyboardButton(
                "Перейти на сайт Межбанк онлайн",
                url="https://minfin.com.ua/currency/mb/usd/",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)


# Функция для отправки курса валют в канал
async def send_rate_to_channel(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    channel_id = os.getenv("channel_id")  # Ваш ID канала
    rate = get_exchange_rate()

    message = f"Текущий курс USD к UAH: {rate}"
    await send_message_with_buttons(channel_id, bot, message)


# Отправка стартового сообщения в канал
async def send_start_message_to_channel(app: Application):
    channel_id = os.getenv("channel_id")  # Ваш ID канала
    message = "Бот запущен! 🚀\nВведите команду /start для начала работы."
    await app.bot.send_message(chat_id=channel_id, text=message)


async def calculate(update, context):
    # Логика функции
    if context.user_data.get("transport_type") == "expenses":
        await calculate_price_with_transport(update, context)
    elif context.user_data.get("transport_type") == "distance":
        await calculate_price_with_transport2(update, context)
    return ConversationHandler.END


# Основная функция
def main():
    TOKEN = "7913394275:AAHrSrQz2-Ev15nXZsbIsQnzEDuzpGaagQA"
    app = Application.builder().token(TOKEN).build()

    # Указываем часовой пояс Польши
    poland_tz = pytz.timezone("Europe/Warsaw")

    # Планировщик задачи: отправка курса в канал дважды в день
    app.job_queue.run_daily(
        send_rate_to_channel, time(hour=7, minute=0, tzinfo=poland_tz)
    )  # 08:00 по польскому времени
    app.job_queue.run_daily(
        send_rate_to_channel, time(hour=9, minute=0, tzinfo=poland_tz)
    )  # 10:00 по польскому времени
    logger.info(f"RAILWAY_PROJECT_NAME: {os.getenv('RAILWAY_PROJECT_NAME')}")
    logger.info(f"channel_id: {os.getenv('channel_id')}")
    print(f"RAILWAY_PROJECT_NAME: {os.getenv('RAILWAY_PROJECT_NAME')}")
    print(f"channel_id: {os.getenv('channel_id')}")
    print("Local Time:", local_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Corrected Time:", corrected_time.strftime("%Y-%m-%d %H:%M:%S"))

    # Добавляем ConversationHandler
    app.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    request_distance, pattern="^price_with_transport$"
                ),
                CallbackQueryHandler(
                    request_distance2, pattern="^price_with_transport2$"
                ),
            ],
            states={
                DISTANCE_INPUT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        calculate,  # Укажите имя функции без async
                    )
                ]
            },
            fallbacks=[],
        )
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
