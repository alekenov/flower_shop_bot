from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Основная клавиатура бота
    """
    keyboard = [
        [KeyboardButton("🌸 Каталог цветов"), KeyboardButton("💰 Цены")],
        [KeyboardButton("🚚 Доставка"), KeyboardButton("⏰ График работы")],
        [KeyboardButton("📞 Связаться с менеджером")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для каталога цветов
    """
    keyboard = [
        [
            InlineKeyboardButton("🌹 Розы", callback_data="catalog_roses"),
            InlineKeyboardButton("🌷 Тюльпаны", callback_data="catalog_tulips")
        ],
        [
            InlineKeyboardButton("🌸 Пионы", callback_data="catalog_peonies"),
            InlineKeyboardButton("💐 Букеты", callback_data="catalog_bouquets")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_delivery_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для раздела доставки
    """
    keyboard = [
        [
            InlineKeyboardButton("🏃 Экспресс", callback_data="delivery_express"),
            InlineKeyboardButton("🚗 Стандарт", callback_data="delivery_standard")
        ],
        [
            InlineKeyboardButton("📍 Зоны доставки", callback_data="delivery_zones"),
            InlineKeyboardButton("💰 Стоимость", callback_data="delivery_price")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
