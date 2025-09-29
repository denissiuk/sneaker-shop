import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === НАСТРОЙКИ ===
BOT_TOKEN = "7948836165:AAE7259aOJU8kbFIkzucQhg3vtJLkz4pm18"  # ← ЗАМЕНИ ЭТО!
ADMIN_ID = 400089744  # ← ЗАМЕНИ НА СВОЙ ID!

# Глобальная переменная для бота
bot = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Посмотреть каталог", callback_data='catalog')],
        [InlineKeyboardButton("Перейти на сайт", url="http://127.0.0.1:5000")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот магазина NANOGI 🛒\n"
        "Нажми кнопку ниже, чтобы посмотреть товары или перейти на сайт.",
        reply_markup=reply_markup
    )

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Здесь можно подключиться к базе — пока заглушка
    products = [
        {"name": "Nike", "price": "129.0 BYN", "photo": "https://via.placeholder.com/200 "},
        {"name": "Salomon", "price": "182.0 BYN", "photo": "https://via.placeholder.com/200 "}
    ]

    for product in products:
        await update.message.reply_photo(
            photo=product["photo"],
            caption=f"<b>{product['name']}</b>\n{product['price']}\n\nДобавь в корзину через сайт!",
            parse_mode="HTML"
        )

    # Кнопка «Перейти на сайт»
    keyboard = [[InlineKeyboardButton("Перейти на сайт", url="http://127.0.0.1:5000")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери товар и добавь в корзину на сайте!", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'catalog':
        await catalog(query, context)

async def notify_admin(message: str):
    """Отправляет сообщение админу в Telegram"""
    if bot:
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=message)
            print("✅ Уведомление отправлено в Telegram")
        except Exception as e:
            print(f"❌ Ошибка Telegram: {e}")

# Функция для запуска бота
def run_bot():
    global bot
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("catalog", catalog))
    application.add_handler(CallbackQueryHandler(button_callback))

    bot = application.bot  # Сохраняем экземпляр бота

    print("🤖 Бот запущен. Ожидание команд...")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
