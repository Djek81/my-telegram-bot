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
from datetime import datetime, timedelta, time
import pytz
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging  # Добавляем модуль для логирования
import os
import json
import subprocess
import base64
from dotenv import load_dotenv

load_dotenv()

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


# Создаем глобальную переменную для хранения учетных данных
credentials = None


# Инициализация учетных данных
def init_credentials():
    global credentials
    try:
        if not os.getenv("GOOGLE_CREDENTIALS"):
            logger.info(
                "Ошибка: Переменная окружения 'GOOGLE_CREDENTIALS' не установлена."
            )
            return False

        google_credentials_json = base64.b64decode(
            os.getenv("GOOGLE_CREDENTIALS")
        ).decode("utf-8")
        credentials_dict = json.loads(google_credentials_json)

        credentials = Credentials.from_service_account_info(credentials_dict)
        logger.info("Учетные данные успешно инициализированы.")
        return True

    except Exception as e:
        logger.info(f"Ошибка инициализации учетных данных: {e}")
        return False


# Получение данных из Google Sheets
def fetch_google_sheet_data(cells, key=os.getenv("key")):
    try:
        # Проверка, что ключ таблицы передан
        if not key:
            logger.info("Ошибка: Переменная окружения 'key' не установлена.")
            return ["Ошибка: Не указан ключ таблицы"] * len(cells)

        # Проверка, что учетные данные были успешно инициализированы
        if credentials is None:
            logger.info("Ошибка: Учетные данные не инициализированы.")
            return ["Ошибка: Учетные данные не найдены"] * len(cells)

        # Авторизация клиента с помощью глобальных учетных данных
        client = gspread.authorize(credentials)

        # Открытие таблицы и листа
        worksheet = client.open_by_key(key).get_worksheet(0)

        # Получение значений из указанных ячеек
        return [worksheet.acell(cell).value for cell in cells]

    except gspread.exceptions.SpreadsheetNotFound:
        logger.info("Ошибка: Таблица не найдена. Проверьте ключ таблицы.")
        return ["Ошибка: Таблица не найдена"] * len(cells)

    except gspread.exceptions.APIError as api_error:
        logger.info(f"Ошибка API Google Sheets: {api_error}")
        return ["Ошибка API"] * len(cells)

    except Exception as e:
        logger.info(f"Неизвестная ошибка при работе с Google Sheets: {e}")
        return ["Ошибка"] * len(cells)


# Инициализация учетных данных перед использованием функции
if init_credentials():
    logger.info("Учетные данные готовы к использованию.")
else:
    logger.info("Не удалось инициализировать учетные данные.")


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
