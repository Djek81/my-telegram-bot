from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)
from datetime import datetime, time
import pytz
import requests
import gspread
from google.oauth2.service_account import Credentials
import logging
import os
from cachetools import TTLCache
import asyncio

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен")

# Часовой пояс
poland_tz = pytz.timezone("Europe/Warsaw")

# Кэш для Google Sheets (5 минут)
cache = TTLCache(maxsize=100, ttl=300)

# Этапы диалога
DISTANCE_INPUT = 1


# Обработка ошибок и логирование
def log_error(error_msg):
    logger.error(f"Помилка: {error_msg}")


# Функция для получения данных из Google Sheets
def fetch_google_sheet_data(cells):
    cache_key = tuple(cells)
    if cache_key in cache:
        logger.info("Данные взяты из кэша")
        return cache[cache_key]
    try:
        Googlekey = os.getenv("Googlekey")
        logger.info(f"GOOGLE_SHEET_KEY: {Googlekey}")
        credentials_info = {
            "type": "service_account",
            "project_id": "uah-bot-project-448013",
            "private_key_id": "855ed546d5a38199a178c15aebb182bd69087f4d",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCxg6r28NHVuVru\nzPDqRFKihyq8q4AN7znMtLu805dkJ9EkbVXJF/fttMqvTLbuURbflSOfAZ3XLNvh\nxKjjazgJCm2c2XeFfLQJNR/KLpIZupW/mxjd25Kc7rWCDUN4ThfJor33k/G+nhmS\n0bHPN4EMSGrB3PAIz6CS2PB1AhuAgXzENYmjCxAWYrS5oEPI9iUKYZtS2GXuEiK6\nBtCz7mHjLOQQNOUV5d7bDBtbvvwMZ8lokf3Q4TBMrxHiwdf9/zINCMDG9IN6RQwm\nCD4DEQVFDiGRNiyNiYGa9y0Rcy5Ra1SKRtkHjmaC2SNu6X+ASlt7X5bw1s8f6wQx\nD1jNOEz/AgMBAAECggEALDfVLYAddPSgDx4j4Oc2AmBTJ/48frwZlMFshoPakUtN\n0JofpWEAFElVt8cPRlwSq40V+3TGoaP9/cYkH8pEghQD6+9L04eVvTlresyQ/jG5\nPapfzlv0sHzR39x38w7Y5BRS58oFjOsLCcSMW0bDMZEUbsgfTsKRiCLb+vmUajTr\nuLahvKArOIzCXSoOftQala0mxdrhXDJNuKCGrRWs27qKZpRj8lRp7SBqS4fSaxQi\nIVSbFh5+N0cLfDVeh4kICFhCH6zLk6Ka0h/mE0bkFXJavEvaJ2yfGWgb9jXtqTXM\nKZjAtG+qm4VyO4qdbFmVwPth4zqFbDlAxCaRyqSRQQKBgQD3+qimwwTg7l0QzCoG\nnratKL+TLKgBhWhtzl7csZMem/cjSTF6sv0VFLGQmJbrM3Lj7ZAZoqWsrMWlxc4L\n1s2fCp4ITzYtL8t8g2NkACdrO0gaY05aZRtP3TKJ5hppsaH9yqba0/NdBLLgQfzx\nrQKaZh60R1e12uDtek5C+xOK3wKBgQC3QYoWfpS7Ljtx35/M1yh5B5IPoQ8Mz5ny\nuOguAWD0wTSfN5gJSoTcoZNFX2ejqLIzKMMgpxSaadaHpVIYIZ4w3nBj0fnYJHXK\nVdcrmWx9QeQCFpv+dCjnxXbmB7RZkIlyW4AHh3LYRAR0/ua8motrC6uBeXUthLoZ\nA0JFJOuh4QKBgFs6Pb1L1YmiZ158naFd1jqR2RidvxkAKVDsMP3j3gnOuvaiQK+x\nFWYh/MkDOdJBVS0BAphLu8NwtC2uPYUhevfdghHwgi/Re3zNIU1yuQ27+2Spz/N1\narzQ1XzhyCnGDaA+Y2/xtYAs8FmMLTADxAdlNjqAXIYshb8X1Z7Sm3flAoGAZUd3\nhc8XbAu1Fs48hv0yhRFGDBU7OB1UO+0thJ+Gcj6FUqlrAVeJ7lXuCp0brjuBoPya\nOuWcYWq1AerAYE3UG7YT71cQ+f/MibK/ZH06lE9iMDVGqW6RXOapO6BucEGNdQJU\n09RsCFIvFGn8I6hV/SdJ9himRi3gnApNCeHJyIECgYAfe3RC2qs3zAx5vsSYFs39\ny5rzwbWvUFH7ssMi/xtQNiUmSx6UCN2Sr+hERUfSHxl/yfNjyE+ldneYV0KIUr9F\nuA9iRApuTKwmtb6PNGqwc5i/mGi77YsQwi/cZBRDf/yRs0pdgDkVMJ7Y1rGIdcj5\nVmZN764Mq+fZecppKK+/gg==\n-----END PRIVATE KEY-----\n",
            "client_email": "token-key@uah-bot-project-448013.iam.gserviceaccount.com",
            "client_id": "108655560595569800378",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/token-key%40uah-bot-project-448013.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com",
        }
        creds = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        worksheet = client.open_by_key(Googlekey).get_worksheet(0)
        result = [worksheet.acell(cell).value for cell in cells]
        cache[cache_key] = result
        return result
    except Exception as e:
        log_error(f"Ошибка при работе с Google Sheets: {e}")
        return ["Помилка"] * len(cells)


# Получение цен в USD
def get_prices_usd():
    cells = ["F2", "F3", "F4", "F5", "A3", "A4"]
    prices = fetch_google_sheet_data(cells)
    now = datetime.now(poland_tz).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Ціни на дизельне паливо (оновлено {now}):\n"
        f"1. Jasło: {prices[0]}$/t\n"
        f"2. Małaszewicze: {prices[1]}$/t\n"
        f"3. Wola: {prices[2]}$/t\n"
        f"4. Czechowice: {prices[3]}$/t\n"
        f"GASOIL {prices[4]} - {prices[5]}$"
    )


# Получение цен в UAH
def get_prices_uah():
    cells = ["S2", "S3", "S4", "S5", "A3", "A4"]
    prices = fetch_google_sheet_data(cells)
    now = datetime.now(poland_tz).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Ціни на дизельне паливо (оновлено {now}):\n"
        f"1. Jasło: {prices[0]}грн/л\n"
        f"2. Małaszewicze: {prices[1]}грн/л\n"
        f"3. Wola: {prices[2]}грн/л\n"
        f"4. Czechowice: {prices[3]}грн/л\n"
        f"GASOIL {prices[4]} - {prices[5]}$"
    )


# Получение курса USD к UAH
def get_exchange_rate():
    try:
        response = requests.get(
            "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json",
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return data[0]["rate"]
    except Exception as e:
        log_error(f"Ошибка при получении курса валют: {e}")
        return "Ошибка при получении курса."


# Функция для запроса расходов
async def request_distance(update, context):
    update_id = update.update_id
    logger.info(
        f"Вызов request_distance, update_id: {update_id}, chat_id: {update.callback_query.message.chat_id}"
    )
    context.user_data["transport_type"] = "expenses"
    await update.callback_query.message.reply_text(
        "Введіть транспортні витрати до місця призначення в гривнях:"
    )
    return DISTANCE_INPUT


# Функция для запроса расстояния
async def request_distance2(update, context):
    update_id = update.update_id
    logger.info(
        f"Вызов request_distance2, update_id: {update_id}, chat_id: {update.callback_query.message.chat_id}"
    )
    context.user_data["transport_type"] = "distance"
    await update.callback_query.message.reply_text(
        "Введіть відстань до місця призначення в км (тариф для розрахунку 40 грн/км):"
    )
    return DISTANCE_INPUT


# Расчет цены с транспортом (по расходам)
async def calculate_price_with_transport(update, context):
    update_id = update.update_id
    logger.info(
        f"Обработка calculate_price_with_transport, update_id: {update_id}, chat_id: {update.effective_chat.id}"
    )
    try:
        distance = float(update.message.text.strip())
        fca_cells = ["S2", "S3", "S4", "S5", "N2", "N3", "N4", "N5"]
        fca_prices = [
            float(price.replace(",", ".").strip())
            for price in fetch_google_sheet_data(fca_cells)
        ]
        now = datetime.now(poland_tz).strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"Ціни на дизельне паливо з доставкою (запит у гривнях) (оновлено {now}):\n"
            f"1. Jasło: {(fca_prices[0] + distance * fca_prices[4] * 0.001 / 25):.2f} грн/л\n"
            f"2. Małaszewicze: {(fca_prices[1] + distance * fca_prices[5] * 0.001 / 25):.2f} грн/л\n"
            f"3. Wola: {(fca_prices[2] + distance * fca_prices[6] * 0.001 / 25):.2f} грн/л\n"
            f"4. Czechowice: {(fca_prices[3] + distance * fca_prices[7] * 0.001 / 25):.2f} грн/л\n"
        )
        await update.message.reply_text(message)
    except ValueError as e:
        log_error(f"Неверный формат ввода: {e}")
        await update.message.reply_text("Будь ласка, введіть числове значення.")
    return ConversationHandler.END


# Расчет цены с транспортом (по расстоянию)
async def calculate_price_with_transport2(update, context):
    update_id = update.update_id
    logger.info(
        f"Обработка calculate_price_with_transport2, update_id: {update_id}, chat_id: {update.effective_chat.id}"
    )
    try:
        distance = float(update.message.text.strip())
        fca_cells = ["S2", "S3", "S4", "S5", "N2", "N3", "N4", "N5"]
        fca_prices = [
            float(price.replace(",", ".").strip())
            for price in fetch_google_sheet_data(fca_cells)
        ]
        now = datetime.now(poland_tz).strftime("%Y-%m-%d %H:%M:%S")
        message = (
            f"Ціни на дизельне паливо з доставкою (запит у км) (оновлено {now}):\n"
            f"1. Jasło: {(fca_prices[0] + distance * 40 * 2 * fca_prices[4] * 0.001 / 25):.2f} грн/л\n"
            f"2. Małaszewicze: {(fca_prices[1] + distance * 40 * 2 * fca_prices[5] * 0.001 / 25):.2f} грн/л\n"
            f"3. Wola: {(fca_prices[2] + distance * 40 * 2 * fca_prices[6] * 0.001 / 25):.2f} грн/л\n"
            f"4. Czechowice: {(fca_prices[3] + distance * 40 * 2 * fca_prices[7] * 0.001 / 25):.2f} грн/л\n"
        )
        await update.message.reply_text(message)
    except ValueError as e:
        log_error(f"Неверный формат ввода: {e}")
        await update.message.reply_text("Будь ласка, введіть числове значення.")
    return ConversationHandler.END


# Отправка сообщения с меню
async def send_message_with_buttons(chat_id, bot, message):
    keyboard = [
        [
            InlineKeyboardButton("💵 Ціни у доларах", callback_data="refresh_prices"),
            InlineKeyboardButton(
                "🇺🇦 Ціни у гривні", callback_data="refresh_prices_UAH"
            ),
        ],
        [
            InlineKeyboardButton(
                "🚚 Транспорт (витрати)", callback_data="price_with_transport"
            ),
            InlineKeyboardButton(
                "🛣 Транспорт (км)", callback_data="price_with_transport2"
            ),
        ],
        [
            InlineKeyboardButton("📈 Курс НБУ", callback_data="check_again"),
            InlineKeyboardButton(
                "🌐 Межбанк онлайн", url="https://minfin.com.ua/currency/mb/usd/"
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)


# Команда /start
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    update_id = update.update_id
    chat_id = update.effective_chat.id
    logger.info(f"Обработка команды /start, update_id: {update_id}, chat_id: {chat_id}")
    message = "Вітаємо! Оберіть дію з меню нижче:"
    await send_message_with_buttons(chat_id, context.bot, message)


# Команда /menu (ReplyKeyboardMarkup)
async def menu(update, context: ContextTypes.DEFAULT_TYPE):
    update_id = update.update_id
    chat_id = update.effective_chat.id
    logger.info(f"Обработка команды /menu, update_id: {update_id}, chat_id: {chat_id}")
    keyboard = [
        ["Ціни у доларах", "Ціни у гривні"],
        ["Курс НБУ", "Межбанк онлайн"],
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text("Оберіть дію:", reply_markup=reply_markup)


# Обработчик текстовых сообщений от ReplyKeyboardMarkup
async def handle_menu_choice(update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("transport_type"):
        logger.info("Игнорируем текстовый ввод, так как активен ConversationHandler")
        return
    update_id = update.update_id
    text = update.message.text
    logger.info(
        f"Обработка выбора меню: {text}, update_id: {update_id}, chat_id: {update.effective_chat.id}"
    )
    if text == "Ціни у доларах":
        message = get_prices_usd()
    elif text == "Ціни у гривні":
        message = get_prices_uah()
    elif text == "Курс НБУ":
        rate = get_exchange_rate()
        message = f"Поточний курс USD до UAH: {rate}"
    elif text == "Межбанк онлайн":
        message = "Перейдіть за посиланням: https://minfin.com.ua/currency/mb/usd/"
    else:
        message = "Невідома команда."
        logger.warning(f"Неизвестный выбор: {text}")
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())


# Команда /help
async def help_command(update, context: ContextTypes.DEFAULT_TYPE):
    update_id = update.update_id
    logger.info(
        f"Обработка команды /help, update_id: {update_id}, chat_id: {update.effective_chat.id}"
    )
    await update.message.reply_text(
        "Це бот для перевірки цін на паливо та курсу валют. Використовуйте /start або /menu для початку."
    )


# Обработчик кнопок
async def button(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    update_id = update.update_id
    chat_id = query.message.chat_id
    logger.info(
        f"Обработка callback: {query.data}, update_id: {update_id}, chat_id: {chat_id}"
    )
    await query.answer()
    if query.data == "refresh_prices":
        message = get_prices_usd()
    elif query.data == "refresh_prices_UAH":
        message = get_prices_uah()
    elif query.data == "check_again":
        rate = get_exchange_rate()
        message = f"Поточний курс USD до UAH: {rate}"
    else:
        message = "Невідома команда."
        logger.warning(f"Неизвестный callback: {query.data}")
    await query.edit_message_text(
        text=message,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💵 Ціни у доларах", callback_data="refresh_prices"
                    ),
                    InlineKeyboardButton(
                        "🇺🇦 Ціни у гривні", callback_data="refresh_prices_UAH"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "🚚 Транспорт (витрати)", callback_data="price_with_transport"
                    ),
                    InlineKeyboardButton(
                        "🛣 Транспорт (км)", callback_data="price_with_transport2"
                    ),
                ],
                [
                    InlineKeyboardButton("📈 Курс НБУ", callback_data="check_again"),
                    InlineKeyboardButton(
                        "🌐 Межбанк онлайн",
                        url="https://minfin.com.ua/currency/mb/usd/",
                    ),
                ],
            ]
        ),
    )


# Отправка курса в канал
async def send_rate_to_channel(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    channel_id = os.getenv("channel_id")
    rate = get_exchange_rate()
    message = f"Поточний курс USD до UAH: {rate}"
    await send_message_with_buttons(channel_id, bot, message)


# Стартовая сообщение в канал
async def send_start_message_to_channel(app: Application):
    channel_id = os.getenv("channel_id")
    message = "Бот запущено! 🚀\nВведіть команду /start для початку роботи."
    await app.bot.send_message(chat_id=channel_id, text=message)


# Обработчик диалога
async def calculate(update, context):
    update_id = update.update_id
    logger.info(
        f"Обработка calculate, update_id: {update_id}, chat_id: {update.effective_chat.id}"
    )
    if context.user_data.get("transport_type") == "expenses":
        await calculate_price_with_transport(update, context)
    elif context.user_data.get("transport_type") == "distance":
        await calculate_price_with_transport2(update, context)
    return ConversationHandler.END


# Асинхронная инициализация
async def initialize_bot(app: Application):
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook удален, переключение на polling")
    await send_start_message_to_channel(app)


# Основная функция
def main():
    app = Application.builder().token(TOKEN).build()

    # Выполняем инициализацию асинхронно
    asyncio.run(initialize_bot(app))

    app.job_queue.run_daily(
        send_rate_to_channel, time(hour=7, minute=0, tzinfo=poland_tz)
    )
    app.job_queue.run_daily(
        send_rate_to_channel, time(hour=9, minute=0, tzinfo=poland_tz)
    )

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
                    MessageHandler(filters.TEXT & ~filters.COMMAND, calculate)
                ]
            },
            fallbacks=[],
            per_message=True,
        )
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))
    app.add_handler(
        CallbackQueryHandler(
            button, pattern="^(refresh_prices|refresh_prices_UAH|check_again)$"
        )
    )

    logger.info("Бот запущен")
    app.run_polling(timeout=30, drop_pending_updates=True)


if __name__ == "__main__":
    main()
