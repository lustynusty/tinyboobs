"""
Telegram бот для продажи цифровых и физических товаров
Версия для python-telegram-bot 21.1.1
- Оплата звёздами Telegram
- Админ-панель с просмотром фото
- Управление товарами
"""

import json
import os
import logging
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, PreCheckoutQueryHandler, ContextTypes
)

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

# ====== ДОБАВЬТЕ ЭТОТ БЛОК ДЛЯ ОТЛАДКИ ======
print("=" * 50)
print("🔍 ДИАГНОСТИКА ПЕРЕМЕННЫХ:")
print(f"BOT_TOKEN получен: {'✅ ДА' if BOT_TOKEN else '❌ НЕТ'}")
if BOT_TOKEN:
    print(f"Длина токена: {len(BOT_TOKEN)} символов")
    print(f"Первые 10 символов: {BOT_TOKEN[:10]}...")
    print(f"Последние 5 символов: ...{BOT_TOKEN[-5:]}")
else:
    print("❌ BOT_TOKEN не найден!")
    print("Все переменные окружения:")
    for key, value in os.environ.items():
        if "TOKEN" in key or "BOT" in key:  # Покажем только похожие переменные
            print(f"  {key}: {value[:10]}...")
print("=" * 50)
# ====== КОНЕЦ БЛОКА ОТЛАДКИ ======

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Имя файла с товарами
DB_FILE = "database.json"

# ================== Функции для работы с JSON ==================
def load_products():
    """Загружает список товаров из JSON-файла."""
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        empty_products = {"digital": [], "physical": []}
        save_products(empty_products)
        return empty_products
    except json.JSONDecodeError:
        empty_products = {"digital": [], "physical": []}
        save_products(empty_products)
        return empty_products

def save_products(products):
    """Сохраняет товары в JSON-файл."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

# ================== Команда /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие и главное меню."""
    user = update.effective_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n"
        "Я так ждала тебя... 🌙✨\n"
        "Сегодня как раз тот вечер, когда хочется устроить личный показ.\n"
        "У меня накопилась целая коллекция новых фото и кое-что интересное из гардероба.\n"
        "Думаю, тебе стоит это увидеть... 💋🔥\n"
        "Только ⭐ Звезды Telegram. Безопасно и без следов"
    )
    
    keyboard = [
        [InlineKeyboardButton("📸 Цифровые товары (фото)", callback_data="menu_digital")],
        [InlineKeyboardButton("👙 Физические товары (бельё)", callback_data="menu_physical")],
    ]
    
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# ================== Обработка нажатий на кнопки ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все нажатия на инлайн-кнопки."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    products = load_products()

    # === Главное меню ===
    if data == "main_menu":
        await show_main_menu(query, user_id)
    
    # === Меню цифровых товаров ===
    elif data == "menu_digital":
        await show_digital_menu(query, products)
    
    # === Меню физических товаров ===
    elif data == "menu_physical":
        await show_physical_menu(query, products)
    
    # === Покупка цифрового товара ===
    elif data.startswith("buy_digital_"):
        await buy_digital(query, context, data, products)
    
    # === Покупка физического товара ===
    elif data.startswith("buy_physical_"):
        await buy_physical_start(query, context, data, products)
    
    # === Админ-панель ===
    elif data == "admin_panel" and user_id in ADMIN_IDS:
        await show_admin_panel(query)
    
    # === Добавление товаров ===
    elif data == "admin_add_digital" and user_id in ADMIN_IDS:
        await start_add_digital(query, context)
    elif data == "admin_add_physical" and user_id in ADMIN_IDS:
        await start_add_physical(query, context)
    
    # === Списки товаров ===
    elif data == "admin_list_digital" and user_id in ADMIN_IDS:
        await show_digital_list(query, products)
    elif data == "admin_list_physical" and user_id in ADMIN_IDS:
        await show_physical_list(query, products)
    
    # === Просмотр фото ===
    elif data == "admin_view_photos_digital" and user_id in ADMIN_IDS:
        await admin_view_photos_digital(query, products)
    elif data == "admin_view_photos_physical" and user_id in ADMIN_IDS:
        await admin_view_photos_physical(query, products)
    elif data == "admin_view_all_photos" and user_id in ADMIN_IDS:
        await admin_view_all_photos(update, context)
    elif data.startswith("admin_show_photo_") and user_id in ADMIN_IDS:
        await admin_show_photo(update, context)
    
    # === Изменение цены ===
    elif data.startswith("admin_edit_price_digital_") and user_id in ADMIN_IDS:
        await edit_price_digital(query, context, data)
    elif data.startswith("admin_edit_price_physical_") and user_id in ADMIN_IDS:
        await edit_price_physical(query, context, data)
    
    # === Удаление товаров ===
    elif data.startswith("admin_delete_digital_") and user_id in ADMIN_IDS:
        await delete_digital(query, data, products)
    elif data.startswith("admin_delete_physical_") and user_id in ADMIN_IDS:
        await delete_physical(query, data, products)

# ================== Функции меню ==================
async def show_main_menu(query, user_id):
    """Показывает главное меню."""
    keyboard = [
        [InlineKeyboardButton("📸 Цифровые товары", callback_data="menu_digital")],
        [InlineKeyboardButton("👙 Физические товары", callback_data="menu_physical")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🛠 Админ-панель", callback_data="admin_panel")])
    await query.edit_message_text("Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_digital_menu(query, products):
    """Показывает меню цифровых товаров."""
    digital = products["digital"]
    if not digital:
        text = "📭 В этом разделе пока нет товаров."
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    else:
        text = "📸 Цифровые товары:\n\n"
        keyboard = []
        for i, item in enumerate(digital):
            text += f"{i+1}. {item['name']} — {item['price']} ⭐️\n"
            keyboard.append([InlineKeyboardButton(f"Купить {item['name']}", callback_data=f"buy_digital_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_physical_menu(query, products):
    """Показывает меню физических товаров."""
    physical = products["physical"]
    if not physical:
        text = "📭 В этом разделе пока нет товаров."
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
    else:
        text = "👙 Физические товары:\n\n"
        keyboard = []
        for i, item in enumerate(physical):
            text += f"{i+1}. {item['name']} — {item['price']} ⭐️\n"
            keyboard.append([InlineKeyboardButton(f"Купить {item['name']}", callback_data=f"buy_physical_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================== Админ-панель ==================
async def show_admin_panel(query):
    """Показывает админ-панель со всеми функциями."""
    text = "🛠 Админ-панель\n\nВыберите действие:"
    keyboard = [
        [InlineKeyboardButton("➕ Добавить цифровой товар", callback_data="admin_add_digital")],
        [InlineKeyboardButton("➕ Добавить физический товар", callback_data="admin_add_physical")],
        [InlineKeyboardButton("📋 Список цифровых товаров", callback_data="admin_list_digital")],
        [InlineKeyboardButton("📋 Список физических товаров", callback_data="admin_list_physical")],
        [InlineKeyboardButton("👁 Просмотр фото (цифровые)", callback_data="admin_view_photos_digital")],
        [InlineKeyboardButton("👁 Просмотр фото (физические)", callback_data="admin_view_photos_physical")],
        [InlineKeyboardButton("🖼 Все фото сразу", callback_data="admin_view_all_photos")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_digital_list(query, products):
    """Показывает список цифровых товаров с кнопками управления."""
    digital = products["digital"]
    if not digital:
        await query.edit_message_text(
            "Цифровых товаров нет.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return
    
    text = "📸 Цифровые товары:\n"
    keyboard = []
    for i, item in enumerate(digital):
        has_photo = "✅" if item.get("file_id") else "❌"
        text += f"\n{i+1}. {item['name']} — {item['price']} ⭐️ {has_photo}"
        keyboard.append([
            InlineKeyboardButton(f"✏️ Цена {i+1}", callback_data=f"admin_edit_price_digital_{i}"),
            InlineKeyboardButton(f"❌ Удалить {i+1}", callback_data=f"admin_delete_digital_{i}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_physical_list(query, products):
    """Показывает список физических товаров с кнопками управления."""
    physical = products["physical"]
    if not physical:
        await query.edit_message_text(
            "Физических товаров нет.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return
    
    text = "👙 Физические товары:\n"
    keyboard = []
    for i, item in enumerate(physical):
        has_photo = "✅" if item.get("file_id") else "❌"
        text += f"\n{i+1}. {item['name']} — {item['price']} ⭐️ {has_photo}"
        keyboard.append([
            InlineKeyboardButton(f"✏️ Цена {i+1}", callback_data=f"admin_edit_price_physical_{i}"),
            InlineKeyboardButton(f"❌ Удалить {i+1}", callback_data=f"admin_delete_physical_{i}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================== Функции просмотра фото для админа ==================
async def admin_view_photos_digital(query, products):
    """Показывает все цифровые товары с фото для предпросмотра."""
    digital = products["digital"]
    if not digital:
        await query.edit_message_text(
            "📭 Цифровых товаров нет.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return
    
    text = "📸 Цифровые товары (выберите для просмотра фото):\n\n"
    keyboard = []
    
    for i, item in enumerate(digital):
        has_photo = "✅" if item.get("file_id") else "❌"
        text += f"{i+1}. {item['name']} — {item['price']} ⭐️ {has_photo}\n"
        if item.get("file_id"):
            keyboard.append([InlineKeyboardButton(f"👁 Показать фото {i+1}: {item['name']}", callback_data=f"admin_show_photo_digital_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_view_photos_physical(query, products):
    """Показывает все физические товары с фото для предпросмотра."""
    physical = products["physical"]
    if not physical:
        await query.edit_message_text(
            "📭 Физических товаров нет.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return
    
    text = "👙 Физические товары (выберите для просмотра фото):\n\n"
    keyboard = []
    
    for i, item in enumerate(physical):
        has_photo = "✅" if item.get("file_id") else "❌"
        text += f"{i+1}. {item['name']} — {item['price']} ⭐️ {has_photo}\n"
        if item.get("file_id"):
            keyboard.append([InlineKeyboardButton(f"👁 Показать фото {i+1}: {item['name']}", callback_data=f"admin_show_photo_physical_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_show_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает фото конкретного товара."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split("_")
    
    # Формат: admin_show_photo_digital_0 или admin_show_photo_physical_0
    product_type = parts[3]  # digital или physical
    index = int(parts[4])
    
    products = load_products()
    
    if product_type == "digital" and index < len(products["digital"]):
        item = products["digital"][index]
        photo_file_id = item.get("file_id")
        
        if photo_file_id:
            # Отправляем фото в чат
            await query.message.delete()  # Удаляем сообщение с меню
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=photo_file_id,
                caption=f"📸 {item['name']}\nЦена: {item['price']} ⭐️\n\nID фото: {photo_file_id}"
            )
            # Возвращаемся к списку фото
            await admin_view_photos_digital(query, products)
        else:
            await query.edit_message_text(
                f"❌ У товара «{item['name']}» нет фото.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_view_photos_digital")]])
            )
    
    elif product_type == "physical" and index < len(products["physical"]):
        item = products["physical"][index]
        photo_file_id = item.get("file_id")
        
        if photo_file_id:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=photo_file_id,
                caption=f"👙 {item['name']}\nЦена: {item['price']} ⭐️\n\nID фото: {photo_file_id}"
            )
            await admin_view_photos_physical(query, products)
        else:
            await query.edit_message_text(
                f"❌ У товара «{item['name']}» нет фото.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_view_photos_physical")]])
            )
    else:
        await query.edit_message_text(
            "❌ Товар не найден.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )

async def admin_view_all_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все фото всех товаров (для быстрого просмотра)."""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    digital = products["digital"]
    physical = products["physical"]
    
    # Сначала показываем цифровые товары
    digital_with_photo = [item for item in digital if item.get("file_id")]
    
    if digital_with_photo:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="📸 Цифровые товары с фото:"
        )
        
        for item in digital_with_photo:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=item["file_id"],
                caption=f"📸 {item['name']} — {item['price']} ⭐️"
            )
    
    # Затем физические товары
    physical_with_photo = [item for item in physical if item.get("file_id")]
    
    if physical_with_photo:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="👙 Физические товары с фото:"
        )
        
        for item in physical_with_photo:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=item["file_id"],
                caption=f"👙 {item['name']} — {item['price']} ⭐️"
            )
    
    if not digital_with_photo and not physical_with_photo:
        await query.edit_message_text(
            "📭 Нет товаров с фото.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
    else:
        # Возвращаемся в админ-панель
        await show_admin_panel(query)

# ================== Функции админа для добавления ==================
async def start_add_digital(query, context):
    """Начинает добавление цифрового товара."""
    context.user_data["adding_product"] = {"type": "digital", "step": "name"}
    await query.edit_message_text(
        "Введите название цифрового товара:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]])
    )

async def start_add_physical(query, context):
    """Начинает добавление физического товара."""
    context.user_data["adding_product"] = {"type": "physical", "step": "name"}
    await query.edit_message_text(
        "Введите название физического товара:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]])
    )

async def edit_price_digital(query, context, data):
    """Начинает изменение цены цифрового товара."""
    index = int(data.split("_")[-1])
    context.user_data["editing_price"] = {"type": "digital", "index": index}
    await query.edit_message_text(
        "Введите новую цену (в звёздах):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_list_digital")]])
    )

async def edit_price_physical(query, context, data):
    """Начинает изменение цены физического товара."""
    index = int(data.split("_")[-1])
    context.user_data["editing_price"] = {"type": "physical", "index": index}
    await query.edit_message_text(
        "Введите новую цену (в звёздах):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_list_physical")]])
    )

async def delete_digital(query, data, products):
    """Удаляет цифровой товар."""
    index = int(data.split("_")[-1])
    if index < len(products["digital"]):
        deleted = products["digital"].pop(index)
        save_products(products)
        await query.edit_message_text(
            f"✅ Товар «{deleted['name']}» удалён.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_digital")]])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка: товар не найден.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_digital")]])
        )

async def delete_physical(query, data, products):
    """Удаляет физический товар."""
    index = int(data.split("_")[-1])
    if index < len(products["physical"]):
        deleted = products["physical"].pop(index)
        save_products(products)
        await query.edit_message_text(
            f"✅ Товар «{deleted['name']}» удалён.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_physical")]])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка: товар не найден.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_physical")]])
        )

# ================== Функции покупок ==================
async def buy_digital(query, context, data, products):
    """Обрабатывает начало покупки цифрового товара."""
    index = int(data.split("_")[-1])
    product = products["digital"][index]
    
    context.user_data["pending_purchase"] = {
        "type": "digital",
        "title": product["name"],
        "price": product["price"],
        "photo_file_id": product.get("file_id")
    }
    
    await send_invoice(query, context, product["name"], product["price"], "Цифровой товар")

async def buy_physical_start(query, context, data, products):
    """Начинает процесс покупки физического товара."""
    index = int(data.split("_")[-1])
    product = products["physical"][index]
    
    context.user_data["temp_physical"] = {
        "index": index,
        "name": product["name"],
        "price": product["price"]
    }
    context.user_data["awaiting_address"] = True
    
    await query.edit_message_text(
        "Пожалуйста, введите адрес доставки (город, улица, дом, квартира):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="menu_physical")]])
    )

async def send_invoice(query, context, title, price, description):
    """Отправляет инвойс для оплаты звёздами."""
    prices = [LabeledPrice(label=title, amount=price)]
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=title,
        description=description,
        payload="custom_payload",
        provider_token="",
        currency="XTR",
        prices=prices
    )

# ================== Обработка текстовых сообщений ==================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения."""
    user_id = update.effective_user.id
    text = update.message.text

    # Ожидание адреса для физического товара
    if context.user_data.get("awaiting_address"):
        context.user_data["delivery_address"] = text
        context.user_data["awaiting_address"] = False
        context.user_data["awaiting_comment"] = True
        await update.message.reply_text(
            "Спасибо! Теперь введите комментарий к заказу (или отправьте '-' если нет):"
        )
        return

    # Ожидание комментария
    if context.user_data.get("awaiting_comment"):
        context.user_data["delivery_comment"] = text if text != "-" else ""
        context.user_data["awaiting_comment"] = False

        physical_info = context.user_data.get("temp_physical")
        if physical_info:
            context.user_data["pending_purchase"] = {
                "type": "physical",
                "title": physical_info["name"],
                "price": physical_info["price"]
            }
            await send_invoice(update, context, physical_info["name"], physical_info["price"], "Физический товар")
            context.user_data.pop("temp_physical", None)
        return

    # Добавление товара админом
    if context.user_data.get("adding_product") and user_id in ADMIN_IDS:
        await add_product_step(update, context)
        return

    # Изменение цены админом
    if context.user_data.get("editing_price") and user_id in ADMIN_IDS:
        await change_price_step(update, context, text)
        return

    await update.message.reply_text("Используйте кнопки меню.")

async def add_product_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пошаговое добавление товара админом."""
    product_data = context.user_data["adding_product"]
    step = product_data["step"]
    text = update.message.text

    if step == "name":
        product_data["name"] = text
        product_data["step"] = "price"
        await update.message.reply_text("Введите цену (в звёздах):")
    
    elif step == "price":
        try:
            price = int(text)
            product_data["price"] = price
            product_data["step"] = "photo"
            await update.message.reply_text("Отправьте фото (или напишите 'нет'):")
        except ValueError:
            await update.message.reply_text("❌ Цена должна быть числом. Попробуйте снова:")
    
    elif step == "photo":
        # Сохраняем товар без фото
        products = load_products()
        product_type = product_data["type"]
        new_item = {
            "name": product_data["name"],
            "price": product_data["price"],
            "file_id": None
        }
        products[product_type].append(new_item)
        save_products(products)
        context.user_data.pop("adding_product")
        await update.message.reply_text(
            "✅ Товар добавлен!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В админку", callback_data="admin_panel")]])
        )

async def change_price_step(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Изменение цены товара админом."""
    try:
        new_price = int(text)
    except ValueError:
        await update.message.reply_text("❌ Цена должна быть числом. Попробуйте снова:")
        return
    
    edit_info = context.user_data["editing_price"]
    product_type = edit_info["type"]
    index = edit_info["index"]
    
    products = load_products()
    
    if product_type == "digital" and index < len(products["digital"]):
        products["digital"][index]["price"] = new_price
        save_products(products)
        await update.message.reply_text(
            "✅ Цена обновлена!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_digital")]])
        )
    elif product_type == "physical" and index < len(products["physical"]):
        products["physical"][index]["price"] = new_price
        save_products(products)
        await update.message.reply_text(
            "✅ Цена обновлена!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_list_physical")]])
        )
    else:
        await update.message.reply_text("❌ Ошибка: товар не найден.")
    
    context.user_data.pop("editing_price")

# ================== Обработка фото ==================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет фото при добавлении товара админом."""
    user_id = update.effective_user.id
    
    if not context.user_data.get("adding_product") or user_id not in ADMIN_IDS:
        await update.message.reply_text("Сначала выберите команду добавления товара.")
        return
    
    product_data = context.user_data["adding_product"]
    if product_data.get("step") != "photo":
        await update.message.reply_text("Сейчас не требуется фото.")
        return
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    products = load_products()
    product_type = product_data["type"]
    new_item = {
        "name": product_data["name"],
        "price": product_data["price"],
        "file_id": file_id
    }
    products[product_type].append(new_item)
    save_products(products)
    context.user_data.pop("adding_product")
    
    await update.message.reply_text(
        "✅ Товар с фото добавлен!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В админку", callback_data="admin_panel")]])
    )

# ================== Платёжные обработчики ==================
async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предварительная проверка платежа."""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает успешный платёж."""
    user_id = update.effective_user.id
    purchase = context.user_data.get("pending_purchase")
    
    if not purchase:
        await update.message.reply_text("Оплата прошла, но товар не определён. Свяжитесь с администратором.")
        return

    if purchase["type"] == "digital":
        # Отправляем фото
        photo_file_id = purchase.get("photo_file_id")
        if photo_file_id:
            await update.message.reply_photo(
                photo=photo_file_id,
                caption="Спасибо за покупку! Вот ваше фото. 💕"
            )
        else:
            await update.message.reply_text(
                "Спасибо за покупку! Фото будет отправлено отдельно."
            )
        context.user_data.pop("pending_purchase", None)

    elif purchase["type"] == "physical":
        # Уведомляем админов о заказе
        address = context.user_data.get("delivery_address")
        comment = context.user_data.get("delivery_comment", "")
        
        if not address:
            await update.message.reply_text(
                "Оплата прошла, но адрес не указан. Напишите администратору."
            )
            return

        admin_text = (
            f"🛒 НОВЫЙ ЗАКАЗ (ОПЛАЧЕН)!\n"
            f"Товар: {purchase['title']}\n"
            f"Покупатель: @{update.effective_user.username} (ID: {user_id})\n"
            f"Адрес: {address}\n"
            f"Комментарий: {comment}\n"
            f"Сумма: {purchase['price']} ⭐️"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, admin_text)
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

        await update.message.reply_text(
            "Спасибо за покупку! Ваш заказ передан в обработку. 💌"
        )
        
        # Очищаем данные
        context.user_data.pop("pending_purchase", None)
        context.user_data.pop("delivery_address", None)
        context.user_data.pop("delivery_comment", None)

# ================== Запуск бота ==================
def main():
    """Главная функция запуска бота."""
    print("🚀 Запуск бота...")
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Запускаем бота
    print("✅ Бот успешно запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling()

if __name__ == "__main__":
    main()