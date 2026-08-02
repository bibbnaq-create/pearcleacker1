import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = "7847307838:AAGoxXnPMy8q6AdCg9tV2u6wsuZUoSB7Llo"
DATA_FILE = "clicker_data.json"
ADMINS = ["8888187728"]

# ============================================
# NFT КОНФИГУРАЦИЯ
# ============================================

NFT_COLLECTIONS = {
    "1": {
        "id": "1",
        "name": "🔥 Дракон",
        "emoji": "🐉",
        "price": 15000,
        "total": 5,
        "rarity": "Легендарный",
        "bonus": 30,
        "description": "+30% к силе клика"
    },
    "2": {
        "id": "2",
        "name": "💎 Кристалл",
        "emoji": "💎",
        "price": 8000,
        "total": 5,
        "rarity": "Редкий",
        "bonus": 15,
        "description": "+15% к силе клика"
    },
    "3": {
        "id": "3",
        "name": "👑 Корона",
        "emoji": "👑",
        "price": 25000,
        "total": 5,
        "rarity": "Мифический",
        "bonus": 50,
        "description": "+50% к силе клика"
    }
}

# ============================================
# ХРАНИЛИЩЕ ДАННЫХ (JSON)
# ============================================

class ClickerData:
    def __init__(self):
        self.users = {}
        self.nft_market = []
        self.promocodes = {}
        self.load()

    def load(self):
        global ADMINS
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.nft_market = data.get('nft_market', [])
                    self.promocodes = data.get('promocodes', {})
                    admins = data.get('admins', [])
                    if admins:
                        ADMINS = admins
            except:
                self.users = {}
                self.nft_market = []
                self.promocodes = {}
        else:
            self.users = {}
            self.nft_market = []
            self.promocodes = {}

    def save(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'users': self.users,
                'nft_market': self.nft_market,
                'promocodes': self.promocodes,
                'admins': ADMINS
            }, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id):
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'balance': 0,
                'click_power': 1,
                'level': 1,
                'xp': 0,
                'boosts': {
                    'multi_click': 0,
                    'auto_clicker': 0,
                    'click_bonus': 0,
                },
                'total_clicks': 0,
                'streak': 0,
                'last_streak': datetime.now().isoformat(),
                'last_daily': None,
                'banned': False,
                'warns': 0,
                'nft_inventory': [],
                'daily_bonus_streak': 0,
                'credit_limit': 0,
                'credit_used': 0,
                'credit_pending': 0,
                'credit_history': [],
                'total_credit_taken': 0,
                'used_promocodes': [],
            }
            self.save()
        else:
            user = self.users[user_id]
            changed = False
            for key in ['level', 'xp', 'boosts', 'total_clicks', 'streak', 'last_streak', 'last_daily', 'banned', 'warns', 'click_power', 'nft_inventory', 'daily_bonus_streak', 'credit_limit', 'credit_used', 'credit_pending', 'credit_history', 'total_credit_taken', 'used_promocodes']:
                if key not in user:
                    if key == 'boosts':
                        user['boosts'] = {'multi_click': 0, 'auto_clicker': 0, 'click_bonus': 0}
                    elif key == 'level':
                        user['level'] = 1
                    elif key == 'click_power':
                        user['click_power'] = 1
                    elif key == 'nft_inventory':
                        user['nft_inventory'] = []
                    elif key == 'credit_history':
                        user['credit_history'] = []
                    elif key == 'used_promocodes':
                        user['used_promocodes'] = []
                    else:
                        user[key] = 0 if key != 'last_streak' and key != 'last_daily' else None
                    changed = True
            if changed:
                self.save()
        return self.users[user_id]

    def update_user(self, user_id, data):
        user_id = str(user_id)
        self.users[user_id] = data
        self.save()

    def get_all_users(self):
        return self.users

    def get_nft_market(self):
        return self.nft_market

    def add_nft_to_market(self, nft_data):
        self.nft_market.append(nft_data)
        self.save()

    def remove_nft_from_market(self, nft_id):
        self.nft_market = [n for n in self.nft_market if n['id'] != nft_id]
        self.save()

    def get_nft_by_id(self, nft_id):
        for nft in self.nft_market:
            if nft['id'] == nft_id:
                return nft
        return None

    def get_promocode(self, code):
        return self.promocodes.get(code, None)

    def create_promocode(self, code, reward, max_uses, expires_in_days=7):
        self.promocodes[code] = {
            'reward': reward,
            'max_uses': max_uses,
            'used': 0,
            'created': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(days=expires_in_days)).isoformat(),
            'users': []
        }
        self.save()
        return True

    def use_promocode(self, code, user_id):
        promocode = self.promocodes.get(code)
        if not promocode:
            return False, "Промокод не найден"
        
        if promocode['used'] >= promocode['max_uses']:
            return False, "Промокод уже использован максимальное количество раз"
        
        if datetime.fromisoformat(promocode['expires']) < datetime.now():
            return False, "Промокод истёк"
        
        if user_id in promocode['users']:
            return False, "Вы уже использовали этот промокод"
        
        promocode['used'] += 1
        promocode['users'].append(user_id)
        self.save()
        return True, promocode['reward']

    def get_all_promocodes(self):
        return self.promocodes

db = ClickerData()

# ============================================
# КЛАВИАТУРА
# ============================================

def get_main_keyboard():
    keyboard = [
        ["🖱️ КЛИК", "👤 Профиль"],
        ["💰 Магазин", "🏆 Топ"],
        ["🎁 Бонус", "🛒 NFT"],
        ["🏦 Банк | 💸 Перевод"],
        ["🎫 Промокод", "❓ Помощь"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        ["🖱️ КЛИК", "👤 Профиль"],
        ["💰 Магазин", "🏆 Топ"],
        ["🎁 Бонус", "🛒 NFT"],
        ["🏦 Банк | 💸 Перевод"],
        ["🎫 Промокод", "⚙️ Админ"],
        ["❓ Помощь"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def format_num(num):
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(int(num))

def get_power(user_data):
    base = user_data.get('click_power', 1)
    boosts = user_data.get('boosts', {})
    
    multi = 1.5 ** boosts.get('multi_click', 0)
    bonus = 1 + (boosts.get('click_bonus', 0) * 0.05)
    
    nft_bonus = 1
    for nft_id in user_data.get('nft_inventory', []):
        if nft_id == "1":
            nft_bonus += 0.3
        elif nft_id == "2":
            nft_bonus += 0.15
        elif nft_id == "3":
            nft_bonus += 0.5
    
    return int(base * multi * bonus * nft_bonus)

def get_xp_to_next(level):
    return int(150 * (level ** 1.8))

def random_message():
    messages = [
        "💥 БАМ!", "🔥 Огонь!", "⚡ Молния!",
        "🎯 Точняк!", "💪 Мощь!", "🚀 Взлёт!",
        "✨ Искра!", "🌟 Звезда!", "🎉 Ура!",
        "💎 Кристалл!", "🌈 Радуга!", "🎊 Праздник!"
    ]
    return random.choice(messages)

def is_admin(user_id):
    return str(user_id) in ADMINS

def generate_nft_id():
    return f"nft_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

def generate_promocode():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(random.choice(letters) for _ in range(8))

MAIN_BUTTONS = [
    "🖱️ КЛИК", "👤 Профиль", "💰 Магазин", "🏆 Топ",
    "🎁 Бонус", "🛒 NFT", "🏦 Банк | 💸 Перевод",
    "🎫 Промокод", "⚙️ Админ", "❓ Помощь"
]

def is_main_button(text):
    return text in MAIN_BUTTONS

# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Игрок"
    
    if username == "cagalo" and str(user_id) not in ADMINS:
        ADMINS.append(str(user_id))
        db.save()
    
    user_data = db.get_user(user_id)
    
    if user_data.get('banned', False):
        await update.message.reply_text("🚫 <b>Вы забанены!</b>", parse_mode="HTML")
        return
    
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    
    await update.message.reply_text(
        f"🍐 <b>Pear Clicker</b>\n\n"
        f"Привет, {username}! 👋\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"💪 Сила: {get_power(user_data)}\n"
        f"📈 Уровень: {user_data['level']}\n"
        f"📦 NFT: {len(user_data.get('nft_inventory', []))}\n\n"
        f"🔥 Нажимай <b>КЛИК</b>!\n"
        f"🛒 Покупай NFT!\n"
        f"🏦 Бери кредиты!\n"
        f"🎫 Вводи промокоды!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user_data = db.get_user(user_id)
    
    if user_data.get('banned', False):
        await update.message.reply_text("🚫 Вы забанены!")
        return
    
    # Обработка состояний
    if context.user_data.get('awaiting_credit'):
        await handle_credit_apply(update, context)
        return
    
    if context.user_data.get('awaiting_credit_take'):
        await handle_credit_take(update, context)
        return
    
    if context.user_data.get('awaiting_transfer'):
        await handle_transfer(update, context)
        return
    
    if context.user_data.get('selling_nft') and text.isdigit():
        await handle_sell_price(update, context)
        return
    
    if context.user_data.get('awaiting_promocode'):
        await handle_promocode_apply(update, context)
        return
    
    if context.user_data.get('creating_promocode'):
        await handle_create_promocode(update, context)
        return
    
    if not is_main_button(text):
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❓ Используй кнопки на клавиатуре!", reply_markup=keyboard)
        return
    
    if text == "🖱️ КЛИК":
        await process_click(update, context)
    elif text == "👤 Профиль":
        await show_profile(update, context)
    elif text == "💰 Магазин":
        await show_shop(update, context)
    elif text == "🏆 Топ":
        await show_top(update, context)
    elif text == "🎁 Бонус":
        await get_daily_bonus(update, context)
    elif text == "🛒 NFT":
        await show_nft_market(update, context)
    elif text == "🏦 Банк | 💸 Перевод":
        await bank_menu(update, context)
    elif text == "🎫 Промокод":
        await apply_promocode(update, context)
    elif text == "⚙️ Админ" and is_admin(user_id):
        await show_admin_panel(update, context)
    elif text == "❓ Помощь":
        await show_help(update, context)

# ============================================
# КЛИК
# ============================================

async def process_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data.get('banned', False):
        await update.message.reply_text("🚫 Вы забанены!")
        return
    
    user_data['streak'] = user_data.get('streak', 0) + 1
    
    power = get_power(user_data)
    streak_bonus = min(user_data['streak'] * 0.01, 1.0)
    earned = int(power * (0.5 + streak_bonus))
    
    if earned < 1:
        earned = 1
    
    user_data['balance'] = user_data.get('balance', 0) + earned
    user_data['total_clicks'] = user_data.get('total_clicks', 0) + 1
    user_data['xp'] = user_data.get('xp', 0) + int(earned * 0.5)
    
    xp_to_next = get_xp_to_next(user_data['level'])
    if user_data['xp'] >= xp_to_next:
        user_data['level'] += 1
        user_data['xp'] = 0
        user_data['click_power'] = user_data.get('click_power', 1) + 1
        await update.message.reply_text(
            f"🎉 <b>УРОВЕНЬ ПОВЫШЕН!</b>\n\n"
            f"📈 Теперь {user_data['level']} уровень!\n"
            f"💪 Сила клика +1!",
            parse_mode="HTML"
        )
    
    db.update_user(user_id, user_data)
    
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    
    msg = (
        f"{random_message()}\n\n"
        f"💰 +{format_num(earned)} монет\n"
        f"🔥 Стрик: {user_data['streak']}x (+{int(streak_bonus * 100)}%)\n"
        f"💪 Сила: {power}\n"
        f"📈 Уровень: {user_data['level']}\n"
        f"💎 Баланс: {format_num(user_data['balance'])}\n"
        f"📦 NFT: {len(user_data.get('nft_inventory', []))}"
    )
    
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="HTML")

# ============================================
# ПРОФИЛЬ
# ============================================

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    username = update.effective_user.username or "Игрок"
    
    xp_to_next = get_xp_to_next(user_data['level'])
    xp_percent = int((user_data.get('xp', 0) / xp_to_next) * 100) if xp_to_next > 0 else 0
    
    nft_count = len(user_data.get('nft_inventory', []))
    
    nft_bonus = 0
    for nft_id in user_data.get('nft_inventory', []):
        if nft_id == "1":
            nft_bonus += 30
        elif nft_id == "2":
            nft_bonus += 15
        elif nft_id == "3":
            nft_bonus += 50
    
    boosts = user_data.get('boosts', {})
    
    msg = (
        f"👤 <b>Профиль</b>\n\n"
        f"Имя: @{username}\n"
        f"📈 Уровень: {user_data['level']}\n"
        f"📊 XP: {format_num(user_data.get('xp', 0))} / {format_num(xp_to_next)} ({xp_percent}%)\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"💪 Сила клика: {get_power(user_data)}\n"
        f"🖱️ Всего кликов: {format_num(user_data.get('total_clicks', 0))}\n"
        f"🔥 Стрик: {user_data.get('streak', 0)}x\n"
        f"📦 NFT: {nft_count} шт.\n"
        f"💎 Бонус от NFT: +{nft_bonus}%\n"
        f"🏦 Кредитный лимит: {format_num(user_data.get('credit_limit', 0))}\n"
        f"💳 Использовано кредитов: {format_num(user_data.get('credit_used', 0))}\n"
        f"🎯 Бусты:\n"
        f"   • Мультиклик: x{1.5 ** boosts.get('multi_click', 0):.1f}\n"
        f"   • Бонус клика: +{boosts.get('click_bonus', 0) * 5}%\n"
        f"   • Автокликер: {boosts.get('auto_clicker', 0)} ур."
    )
    
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="HTML")

# ============================================
# МАГАЗИН С ИНЛАЙН-КНОПКАМИ
# ============================================

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    boosts = user_data.get('boosts', {})
    
    multi_level = boosts.get('multi_click', 0)
    auto_level = boosts.get('auto_clicker', 0)
    bonus_level = boosts.get('click_bonus', 0)
    
    multi_price = 100 * (2 ** multi_level)
    auto_price = 200 * (2 ** auto_level)
    bonus_price = 150 * (2 ** bonus_level)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"🔹 Мультиклик x{1.5 ** multi_level:.1f} — {multi_price}💰",
                callback_data="buy_multi"
            )
        ],
        [
            InlineKeyboardButton(
                f"⚡ Автокликер +{0.5 * auto_level:.1f}/сек — {auto_price}💰",
                callback_data="buy_auto"
            )
        ],
        [
            InlineKeyboardButton(
                f"💎 Бонус клика +{bonus_level * 5}% — {bonus_price}💰",
                callback_data="buy_bonus"
            )
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_shop")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"💰 <b>Магазин улучшений</b>\n\n"
        f"💎 Баланс: <b>{format_num(user_data['balance'])}</b> монет\n\n"
        f"🔹 <b>Мультиклик</b>\n"
        f"   Уровень: {multi_level}\n"
        f"   Эффект: x{1.5 ** multi_level:.1f} к силе\n"
        f"   Цена: {multi_price} монет\n\n"
        f"⚡ <b>Автокликер</b>\n"
        f"   Уровень: {auto_level}\n"
        f"   Эффект: +{0.5 * auto_level:.1f} клик/сек\n"
        f"   Цена: {auto_price} монет\n\n"
        f"💎 <b>Бонус клика</b>\n"
        f"   Уровень: {bonus_level}\n"
        f"   Эффект: +{bonus_level * 5}% к силе\n"
        f"   Цена: {bonus_price} монет\n\n"
        f"<i>Нажми на кнопку для покупки!</i>"
    )
    
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")

async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    
    user_data = db.get_user(user_id)
    if not user_data:
        await query.edit_message_text("❌ Ошибка!")
        return
    
    boosts = user_data.get('boosts', {})
    
    if action == "buy_multi":
        boost_type = 'multi_click'
        base_price = 100
        name = "Мультиклик"
    elif action == "buy_auto":
        boost_type = 'auto_clicker'
        base_price = 200
        name = "Автокликер"
    elif action == "buy_bonus":
        boost_type = 'click_bonus'
        base_price = 150
        name = "Бонус клика"
    elif action == "back_shop":
        # Возврат в меню
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await query.edit_message_text(
            "🍐 <b>Pear Clicker</b>\n\nГлавное меню",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    else:
        await query.edit_message_text("❌ Неизвестная команда!")
        return
    
    level = boosts.get(boost_type, 0)
    price = base_price * (2 ** level)
    
    if user_data['balance'] < price:
        await query.edit_message_text(
            f"❌ <b>Не хватает монет!</b>\n\n"
            f"💰 Нужно: {price} монет\n"
            f"💎 У тебя: {format_num(user_data['balance'])} монет\n\n"
            f"<i>Продолжай кликать и зарабатывать!</i>",
            parse_mode="HTML"
        )
        return
    
    user_data['balance'] -= price
    boosts[boost_type] = boosts.get(boost_type, 0) + 1
    user_data['boosts'] = boosts
    
    db.update_user(user_id, user_data)
    
    await query.edit_message_text(
        f"✅ <b>{name} куплен!</b>\n\n"
        f"📊 Уровень: {boosts[boost_type]}\n"
        f"💎 Остаток: {format_num(user_data['balance'])} монет\n\n"
        f"<i>Продолжай улучшать своего персонажа!</i>",
        parse_mode="HTML"
    )
    
    # Показываем обновлённый магазин
    await show_shop_callback(update, context)

async def show_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    boosts = user_data.get('boosts', {})
    
    multi_level = boosts.get('multi_click', 0)
    auto_level = boosts.get('auto_clicker', 0)
    bonus_level = boosts.get('click_bonus', 0)
    
    multi_price = 100 * (2 ** multi_level)
    auto_price = 200 * (2 ** auto_level)
    bonus_price = 150 * (2 ** bonus_level)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"🔹 Мультиклик x{1.5 ** multi_level:.1f} — {multi_price}💰",
                callback_data="buy_multi"
            )
        ],
        [
            InlineKeyboardButton(
                f"⚡ Автокликер +{0.5 * auto_level:.1f}/сек — {auto_price}💰",
                callback_data="buy_auto"
            )
        ],
        [
            InlineKeyboardButton(
                f"💎 Бонус клика +{bonus_level * 5}% — {bonus_price}💰",
                callback_data="buy_bonus"
            )
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_shop")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"💰 <b>Магазин улучшений</b>\n\n"
        f"💎 Баланс: <b>{format_num(user_data['balance'])}</b> монет\n\n"
        f"🔹 <b>Мультиклик</b>\n"
        f"   Уровень: {multi_level}\n"
        f"   Эффект: x{1.5 ** multi_level:.1f} к силе\n"
        f"   Цена: {multi_price} монет\n\n"
        f"⚡ <b>Автокликер</b>\n"
        f"   Уровень: {auto_level}\n"
        f"   Эффект: +{0.5 * auto_level:.1f} клик/сек\n"
        f"   Цена: {auto_price} монет\n\n"
        f"💎 <b>Бонус клика</b>\n"
        f"   Уровень: {bonus_level}\n"
        f"   Эффект: +{bonus_level * 5}% к силе\n"
        f"   Цена: {bonus_price} монет\n\n"
        f"<i>Нажми на кнопку для покупки!</i>"
    )
    
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="HTML")

# ============================================
# ТОП 10
# ============================================

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_users()
    
    top_users = []
    for uid, data in users.items():
        try:
            user = await context.bot.get_chat(int(uid))
            name = user.username or user.first_name or str(uid)
        except:
            name = str(uid)[:8]
        
        top_users.append({
            'id': uid,
            'name': name,
            'balance': data.get('balance', 0),
            'level': data.get('level', 1),
            'nft_count': len(data.get('nft_inventory', []))
        })
    
    top_users = sorted(top_users, key=lambda x: x['balance'], reverse=True)[:10]
    
    text = "🏆 <b>Топ 10 игроков</b>\n\n"
    
    if not top_users:
        text += "Пока нет игроков 😔"
    else:
        for i, user in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} @{user['name']}\n"
            text += f"   💰 {format_num(user['balance'])} монет\n"
            text += f"   📈 Уровень: {user['level']}\n"
            text += f"   📦 NFT: {user['nft_count']}\n\n"
    
    keyboard = get_admin_keyboard() if is_admin(update.effective_user.id) else get_main_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")

# ============================================
# ЕЖЕДНЕВНЫЙ БОНУС
# ============================================

async def get_daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data.get('last_daily'):
        try:
            last_date = datetime.fromisoformat(user_data['last_daily'])
            if (datetime.now() - last_date).days < 1:
                await update.message.reply_text(
                    "⏳ Бонус уже получен! Жди завтра 🎁",
                    reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
                )
                return
        except:
            pass
    
    nfts = user_data.get('nft_inventory', [])
    has_crown = "3" in nfts
    
    bonus = 50 + (user_data['level'] * 5)
    if has_crown:
        bonus += 25
    
    user_data['balance'] = user_data.get('balance', 0) + bonus
    user_data['last_daily'] = datetime.now().isoformat()
    user_data['daily_bonus_streak'] = user_data.get('daily_bonus_streak', 0) + 1
    
    db.update_user(user_id, user_data)
    
    msg = f"🎁 +{format_num(bonus)} монет!\n\n💰 Баланс: {format_num(user_data['balance'])}"
    if has_crown:
        msg += "\n👑 Бонус от короны +25 монет!"
    
    await update.message.reply_text(
        msg,
        reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    )

# ============================================
# ПОМОЩЬ
# ============================================

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "❓ <b>Помощь</b>\n\n"
        "🖱️ <b>КЛИК</b> — зарабатывай монеты\n"
        "🔥 <b>Стрик</b> — чем чаще кликаешь, тем больше бонус\n"
        "📈 <b>Уровень</b> — повышается с опытом, увеличивает силу\n"
        "💰 <b>Магазин</b> — покупай улучшения:\n"
        "   • Мультиклик — x1.5 к силе\n"
        "   • Автокликер — +0.5 клик/сек\n"
        "   • Бонус клика — +5% к силе\n"
        "🛒 <b>NFT</b> — покупай и продавай NFT\n"
        "🏦 <b>Банк</b> — бери кредиты (до 20,000)\n"
        "💸 <b>Перевод</b> — переводи монеты другим\n"
        "🎁 <b>Бонус</b> — каждый день\n"
        "🎫 <b>Промокод</b> — вводи промокоды\n"
        "🏆 <b>Топ</b> — лучшие игроки\n\n"
        "🍀 <i>Удачи!</i>"
    )
    
    keyboard = get_admin_keyboard() if is_admin(update.effective_user.id) else get_main_keyboard()
    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="HTML")

# ============================================
# ПРОМОКОДЫ
# ============================================

async def apply_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎫 <b>Активация промокода</b>\n\n"
        f"Введи код промокода:\n"
        f"<i>Например: ABC12345</i>\n\n"
        f"🔙 Для отмены напиши 'отмена'",
        parse_mode="HTML"
    )
    context.user_data['awaiting_promocode'] = True

async def handle_promocode_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.upper().strip()
    user_data = db.get_user(user_id)
    
    if text.lower() == "отмена":
        context.user_data.pop('awaiting_promocode', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Отменено!", reply_markup=keyboard)
        return
    
    success, result = db.use_promocode(text, user_id)
    
    if success:
        user_data['balance'] = user_data.get('balance', 0) + result
        db.update_user(user_id, user_data)
        await update.message.reply_text(
            f"✅ <b>Промокод активирован!</b>\n\n"
            f"🎫 Код: {text}\n"
            f"💰 Получено: {result} монет\n"
            f"💎 Новый баланс: {format_num(user_data['balance'])}",
            reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"❌ <b>Ошибка активации!</b>\n\n{result}",
            reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
            parse_mode="HTML"
        )
    
    context.user_data.pop('awaiting_promocode', None)

async def handle_create_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.lower() == "отмена":
        context.user_data.pop('creating_promocode', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Отменено!", reply_markup=keyboard)
        return
    
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Неверный формат!\nИспользуй: награда количество_использований\nНапример: 500 10"
        )
        return
    
    try:
        reward = int(parts[0])
        max_uses = int(parts[1])
    except:
        await update.message.reply_text("❌ Награда и количество должны быть числами!")
        return
    
    if reward < 10:
        await update.message.reply_text("❌ Минимальная награда — 10 монет!")
        return
    if max_uses < 1 or max_uses > 100:
        await update.message.reply_text("❌ Количество использований от 1 до 100!")
        return
    
    code = generate_promocode()
    db.create_promocode(code, reward, max_uses)
    
    await update.message.reply_text(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎫 Код: <code>{code}</code>\n"
        f"💰 Награда: {reward} монет\n"
        f"📊 Использований: {max_uses}\n\n"
        f"<i>Отправь код игрокам!</i>",
        reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
        parse_mode="HTML"
    )
    context.user_data.pop('creating_promocode', None)

# ============================================
# NFT ФУНКЦИИ
# ============================================

async def show_nft_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📦 Мои NFT", callback_data="my_nfts")],
        [InlineKeyboardButton("💰 Продать NFT", callback_data="sell_nft")],
        [InlineKeyboardButton("🏪 Рынок игроков", callback_data="player_market")],
    ]
    
    all_nfts = db.get_nft_market()
    for nft_id, nft_data in NFT_COLLECTIONS.items():
        sold_count = sum(1 for n in all_nfts if n['collection_id'] == nft_id)
        available = nft_data['total'] - sold_count
        if available > 0:
            keyboard.append([InlineKeyboardButton(
                f"{nft_data['emoji']} {nft_data['name']} - {nft_data['price']}💰 ({available} шт.)",
                callback_data=f"buy_nft_{nft_id}"
            )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_nft")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    nfts = user_data.get('nft_inventory', [])
    
    await update.message.reply_text(
        f"🛒 <b>NFT Маркет</b>\n\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"📦 NFT в инвентаре: {len(nfts)}\n\n"
        f"<b>Доступные NFT:</b>\n"
        f"🐉 Дракон — Легендарный (+30% к силе) — 15000💰\n"
        f"💎 Кристалл — Редкий (+15% к силе) — 8000💰\n"
        f"👑 Корона — Мифический (+50% к силе) — 25000💰\n\n"
        f"<i>Выбери действие:</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def buy_nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    collection_id = query.data.replace("buy_nft_", "")
    
    user_data = db.get_user(user_id)
    nft_data = NFT_COLLECTIONS.get(collection_id)
    
    if not nft_data:
        await query.edit_message_text("❌ NFT не найдено!")
        return
    
    all_nfts = db.get_nft_market()
    sold_count = sum(1 for n in all_nfts if n['collection_id'] == collection_id)
    available = nft_data['total'] - sold_count
    
    if available <= 0:
        await query.edit_message_text(f"❌ {nft_data['emoji']} {nft_data['name']} закончились!")
        return
    
    if user_data['balance'] < nft_data['price']:
        await query.edit_message_text(
            f"❌ Не хватает монет!\nНужно: {nft_data['price']}💰\nУ тебя: {format_num(user_data['balance'])}💰",
            parse_mode="HTML"
        )
        return
    
    user_data['balance'] -= nft_data['price']
    user_data['nft_inventory'].append(collection_id)
    
    nft_item = {
        'id': generate_nft_id(),
        'collection_id': collection_id,
        'name': nft_data['name'],
        'emoji': nft_data['emoji'],
        'rarity': nft_data['rarity'],
        'owner_id': str(user_id),
        'price': None,
        'for_sale': False,
        'purchase_date': datetime.now().isoformat(),
    }
    
    db.add_nft_to_market(nft_item)
    db.update_user(user_id, user_data)
    
    keyboard = [[InlineKeyboardButton("🛒 В маркет", callback_data="go_nft_market")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"{nft_data['emoji']} <b>{nft_data['name']}</b>\n"
        f"Редкость: {nft_data['rarity']}\n"
        f"Цена: {nft_data['price']}💰\n"
        f"Остаток: {format_num(user_data['balance'])}💰\n\n"
        f"<i>Теперь этот NFT в твоём инвентаре!</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def show_my_nfts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    nfts = [item for item in db.get_nft_market() if item['owner_id'] == str(user_id)]
    
    if not nfts:
        await query.edit_message_text("📦 <b>У тебя пока нет NFT</b>\n\nКупи их в маркете! 🛒", parse_mode="HTML")
        return
    
    text = "📦 <b>Твои NFT</b>\n\n"
    for nft in nfts:
        collection = NFT_COLLECTIONS.get(nft['collection_id'], {})
        status = "🟢 На продаже" if nft.get('for_sale') else "🔒 В инвентаре"
        text += f"{collection.get('emoji', '🎨')} <b>{nft['name']}</b>\n"
        text += f"   ID: {nft['id'][:8]}...\n"
        text += f"   Статус: {status}\n"
        if nft.get('for_sale') and nft.get('price'):
            text += f"   Цена: {nft['price']}💰\n"
        text += "\n"
    
    keyboard = [[InlineKeyboardButton("🔙 В маркет", callback_data="go_nft_market")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def sell_nft_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    nfts = [item for item in db.get_nft_market() if item['owner_id'] == str(user_id) and not item.get('for_sale', False)]
    
    if not nfts:
        await query.edit_message_text(
            "❌ У тебя нет NFT для продажи.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В маркет", callback_data="go_nft_market")]])
        )
        return
    
    keyboard = []
    for nft in nfts:
        collection = NFT_COLLECTIONS.get(nft['collection_id'], {})
        keyboard.append([InlineKeyboardButton(
            f"{collection.get('emoji', '🎨')} {nft['name']} (ID: {nft['id'][:8]}...)",
            callback_data=f"set_sell_{nft['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 В маркет", callback_data="go_nft_market")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 <b>Продажа NFT</b>\n\nВыбери NFT, который хочешь продать.\nПосле выбора укажи цену в монетах.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def set_sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    nft_id = query.data.replace("set_sell_", "")
    context.user_data['selling_nft'] = nft_id
    
    await query.edit_message_text(
        f"💰 <b>Укажи цену для NFT</b>\n\n"
        f"Напиши цену в монетах (минимальная 500):\n"
        f"<i>Например: 5000</i>\n\n"
        f"🔙 Для отмены напиши 'отмена'",
        parse_mode="HTML"
    )

async def handle_sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.lower() == "отмена":
        context.user_data.pop('selling_nft', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Отменено!", reply_markup=keyboard)
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введи число или напиши 'отмена'!")
        return
    
    price = int(text)
    if price < 500:
        await update.message.reply_text("❌ Минимальная цена — 500 монет!")
        return
    
    nft_id = context.user_data.get('selling_nft')
    if not nft_id:
        await update.message.reply_text("❌ Ошибка! Попробуй снова через маркет.")
        return
    
    nft = db.get_nft_by_id(nft_id)
    if not nft or nft['owner_id'] != str(user_id):
        await update.message.reply_text("❌ NFT не найден или не твой!")
        return
    
    nft['for_sale'] = True
    nft['price'] = price
    db.save()
    
    keyboard = [[InlineKeyboardButton("🛒 В маркет", callback_data="go_nft_market")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ <b>NFT выставлен на продажу!</b>\n\nЦена: {price}💰\nЖди покупателя! 🛒",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    context.user_data.pop('selling_nft', None)

async def player_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    all_nfts = db.get_nft_market()
    for_sale = [n for n in all_nfts if n.get('for_sale', False)]
    
    if not for_sale:
        await query.edit_message_text(
            "🏪 <b>Рынок игроков пуст</b>\n\nНикто не выставил NFT на продажу.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В маркет", callback_data="go_nft_market")]]),
            parse_mode="HTML"
        )
        return
    
    keyboard = []
    for nft in for_sale:
        collection = NFT_COLLECTIONS.get(nft['collection_id'], {})
        seller_name = "Игрок"
        try:
            seller = await context.bot.get_chat(int(nft['owner_id']))
            seller_name = seller.username or seller.first_name or str(nft['owner_id'])[:8]
        except:
            pass
        
        keyboard.append([InlineKeyboardButton(
            f"{collection.get('emoji', '🎨')} {nft['name']} - {nft['price']}💰 (от @{seller_name})",
            callback_data=f"player_buy_{nft['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 В маркет", callback_data="go_nft_market")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏪 <b>Рынок игроков</b>\n\nЗдесь NFT, выставленные другими игроками на продажу.\nНажми на NFT чтобы купить!",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def player_buy_nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    nft_id = query.data.replace("player_buy_", "")
    
    nft = db.get_nft_by_id(nft_id)
    if not nft or not nft.get('for_sale', False):
        await query.edit_message_text("❌ Этот NFT уже продан или недоступен!")
        return
    
    if nft['owner_id'] == str(user_id):
        await query.edit_message_text("❌ Ты не можешь купить свой NFT!")
        return
    
    user_data = db.get_user(user_id)
    seller_data = db.get_user(nft['owner_id'])
    
    price = nft['price']
    
    if user_data['balance'] < price:
        await query.edit_message_text(
            f"❌ Не хватает монет!\nНужно: {price}💰\nУ тебя: {format_num(user_data['balance'])}💰"
        )
        return
    
    user_data['balance'] -= price
    seller_data['balance'] = seller_data.get('balance', 0) + price
    
    old_owner = nft['owner_id']
    nft['owner_id'] = str(user_id)
    nft['for_sale'] = False
    nft['price'] = None
    
    user_data['nft_inventory'].append(nft['id'])
    if nft['id'] in seller_data.get('nft_inventory', []):
        seller_data['nft_inventory'].remove(nft['id'])
    
    db.update_user(user_id, user_data)
    db.update_user(old_owner, seller_data)
    db.save()
    
    try:
        await context.bot.send_message(
            chat_id=int(old_owner),
            text=f"🎉 <b>Твой NFT продан!</b>\n\n"
                 f"{nft.get('emoji', '🎨')} {nft['name']}\n"
                 f"Цена: {price}💰\n"
                 f"Покупатель: @{update.effective_user.username or 'Игрок'}\n"
                 f"Твой баланс: {format_num(seller_data['balance'])}💰",
            parse_mode="HTML"
        )
    except:
        pass
    
    keyboard = [[InlineKeyboardButton("🛒 В маркет", callback_data="go_nft_market")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ <b>Покупка успешна!</b>\n\n"
        f"Ты купил {nft.get('emoji', '🎨')} {nft['name']}\n"
        f"Цена: {price}💰\n"
        f"Твой баланс: {format_num(user_data['balance'])}💰\n\n"
        f"<i>NFT добавлен в инвентарь!</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# ============================================
# БАНК
# ============================================

async def bank_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Заявка на кредит", callback_data="credit_apply")],
        [InlineKeyboardButton("📊 Мои кредиты", callback_data="credit_info")],
        [InlineKeyboardButton("💳 Взять кредит", callback_data="credit_take")],
        [InlineKeyboardButton("💸 Перевод", callback_data="transfer")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_bank")],
    ]
    
    if is_admin(user_id):
        keyboard.insert(1, [InlineKeyboardButton("✅ Одобрить заявки", callback_data="admin_credits")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    available_credit = user_data.get('credit_limit', 0) - user_data.get('credit_used', 0)
    pending = user_data.get('credit_pending', 0)
    
    await update.message.reply_text(
        f"🏦 <b>Банк | Переводы</b>\n\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"📊 Кредитный лимит: {format_num(user_data.get('credit_limit', 0))}\n"
        f"💳 Использовано: {format_num(user_data.get('credit_used', 0))}\n"
        f"💎 Доступно: {format_num(max(0, available_credit))}\n"
        f"⏳ Заявка: {format_num(pending) if pending > 0 else 'Нет'}\n"
        f"📈 Всего взято: {format_num(user_data.get('total_credit_taken', 0))}\n\n"
        f"<i>Максимальный кредит: 20,000 монет</i>\n"
        f"<i>Для перевода напиши: @username сумма</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def transfer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_transfer")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💸 <b>Перевод монет</b>\n\n"
        f"💰 Твой баланс: {format_num(user_data['balance'])}\n\n"
        f"<i>Напиши перевод в формате:</i>\n"
        f"<code>@username сумма</code>\n\n"
        f"<b>Пример:</b>\n"
        f"<code>@john 500</code>\n\n"
        f"📌 Минимальная сумма: 10 монет\n"
        f"🔙 Нажми кнопку 'Назад' для отмены",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    context.user_data['awaiting_transfer'] = True

async def handle_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    user_data = db.get_user(user_id)
    
    if text.lower() == "отмена" or text == "🔙 Назад":
        context.user_data.pop('awaiting_transfer', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Перевод отменён!", reply_markup=keyboard)
        return
    
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ Неверный формат!\nИспользуй: @username сумма\nИли напиши 'отмена' для выхода")
        return
    
    target_username = parts[0].replace('@', '')
    try:
        amount = int(parts[1])
    except:
        await update.message.reply_text("❌ Сумма должна быть числом!")
        return
    
    if amount < 10:
        await update.message.reply_text("❌ Минимальная сумма — 10 монет!")
        return
    
    if user_data['balance'] < amount:
        await update.message.reply_text(
            f"❌ Не хватает монет!\nНужно: {amount}💰\nУ тебя: {format_num(user_data['balance'])}💰"
        )
        return
    
    target_user_id = None
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target_username:
                target_user_id = uid
                break
        except:
            continue
    
    if not target_user_id:
        await update.message.reply_text(f"❌ Пользователь @{target_username} не найден!")
        return
    
    if str(target_user_id) == str(user_id):
        await update.message.reply_text("❌ Нельзя перевести самому себе!")
        return
    
    target_data = db.get_user(target_user_id)
    
    user_data['balance'] -= amount
    target_data['balance'] = target_data.get('balance', 0) + amount
    
    db.update_user(user_id, user_data)
    db.update_user(target_user_id, target_data)
    
    await update.message.reply_text(
        f"✅ <b>Перевод выполнен!</b>\n\n"
        f"💸 Отправлено: {amount}💰\n"
        f"👤 Получатель: @{target_username}\n"
        f"💰 Твой баланс: {format_num(user_data['balance'])}\n\n"
        f"<i>Комиссия: 0%</i>",
        reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
        parse_mode="HTML"
    )
    
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=f"💸 <b>Получен перевод!</b>\n\n"
                 f"💰 +{amount} монет\n"
                 f"👤 Отправитель: @{update.effective_user.username or 'Игрок'}\n"
                 f"💰 Новый баланс: {format_num(target_data['balance'])}",
            parse_mode="HTML"
        )
    except:
        pass
    
    context.user_data.pop('awaiting_transfer', None)

async def credit_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📝 <b>Заявка на кредит</b>\n\n"
        f"Напиши сумму кредита (от 100 до 20,000 монет):\n"
        f"<i>Например: 5000</i>\n\n"
        f"⏳ Заявку рассмотрит администратор.\n"
        f"🔙 Для отмены напиши 'отмена'",
        parse_mode="HTML"
    )
    context.user_data['awaiting_credit'] = True

async def handle_credit_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.lower() == "отмена":
        context.user_data.pop('awaiting_credit', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Заявка отменена!", reply_markup=keyboard)
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введи число или напиши 'отмена'!")
        return
    
    amount = int(text)
    if amount < 100:
        await update.message.reply_text("❌ Минимальная сумма — 100 монет!")
        return
    if amount > 20000:
        await update.message.reply_text("❌ Максимальная сумма — 20,000 монет!")
        return
    
    user_data = db.get_user(user_id)
    
    if user_data.get('credit_pending', 0) > 0:
        await update.message.reply_text("❌ У тебя уже есть заявка на рассмотрении!")
        return
    
    user_data['credit_pending'] = amount
    db.update_user(user_id, user_data)
    
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                chat_id=int(admin_id),
                text=f"📝 <b>Новая заявка на кредит!</b>\n\n"
                     f"👤 Пользователь: @{update.effective_user.username or 'Без username'}\n"
                     f"🆔 ID: {user_id}\n"
                     f"💰 Сумма: {amount} монет\n\n"
                     f"Используй /approve {user_id} {amount} для одобрения\n"
                     f"Используй /decline {user_id} для отказа",
                parse_mode="HTML"
            )
        except:
            pass
    
    await update.message.reply_text(
        f"✅ <b>Заявка отправлена!</b>\n\n"
        f"Сумма: {amount}💰\n"
        f"Статус: ⏳ Ожидает одобрения\n\n"
        f"<i>Администратор рассмотрит заявку в ближайшее время.</i>",
        reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
        parse_mode="HTML"
    )
    context.user_data['awaiting_credit'] = False

async def credit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    history = user_data.get('credit_history', [])
    
    text = (
        f"📊 <b>Информация о кредитах</b>\n\n"
        f"💰 Кредитный лимит: {format_num(user_data.get('credit_limit', 0))}\n"
        f"💳 Использовано: {format_num(user_data.get('credit_used', 0))}\n"
        f"💎 Доступно: {format_num(max(0, user_data.get('credit_limit', 0) - user_data.get('credit_used', 0)))}\n"
        f"📈 Всего взято: {format_num(user_data.get('total_credit_taken', 0))}\n"
        f"⏳ Заявка: {'Есть' if user_data.get('credit_pending', 0) > 0 else 'Нет'}\n\n"
    )
    
    if history:
        text += "<b>История операций:</b>\n"
        for item in history[-5:]:
            text += f"• {item}\n"
    else:
        text += "<i>История пуста</i>"
    
    keyboard = [[InlineKeyboardButton("🔙 В банк", callback_data="go_bank")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def credit_take(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    available = user_data.get('credit_limit', 0) - user_data.get('credit_used', 0)
    
    if available <= 0:
        await query.edit_message_text("❌ <b>Нет доступного кредита!</b>\n\nТвой кредитный лимит исчерпан.", parse_mode="HTML")
        return
    
    await query.edit_message_text(
        f"💳 <b>Взять кредит</b>\n\n"
        f"Доступно: {format_num(available)} монет\n"
        f"Напиши сумму для получения:\n"
        f"<i>Например: {min(1000, available)}</i>\n\n"
        f"🔙 Для отмены напиши 'отмена'",
        parse_mode="HTML"
    )
    context.user_data['awaiting_credit_take'] = True

async def handle_credit_take(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text.lower() == "отмена":
        context.user_data.pop('awaiting_credit_take', None)
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        await update.message.reply_text("❌ Отменено!", reply_markup=keyboard)
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введи число или напиши 'отмена'!")
        return
    
    amount = int(text)
    user_data = db.get_user(user_id)
    
    available = user_data.get('credit_limit', 0) - user_data.get('credit_used', 0)
    
    if amount < 100:
        await update.message.reply_text("❌ Минимальная сумма — 100 монет!")
        return
    if amount > available:
        await update.message.reply_text(f"❌ Доступно только {format_num(available)} монет!")
        return
    
    user_data['balance'] = user_data.get('balance', 0) + amount
    user_data['credit_used'] = user_data.get('credit_used', 0) + amount
    user_data['total_credit_taken'] = user_data.get('total_credit_taken', 0) + amount
    
    if 'credit_history' not in user_data:
        user_data['credit_history'] = []
    user_data['credit_history'].append(f"✅ Взято {amount} монет ({datetime.now().strftime('%d.%m.%Y %H:%M')})")
    
    db.update_user(user_id, user_data)
    
    await update.message.reply_text(
        f"✅ <b>Кредит получен!</b>\n\n"
        f"💰 +{format_num(amount)} монет\n"
        f"💳 Новый баланс: {format_num(user_data['balance'])}\n"
        f"💎 Остаток кредита: {format_num(available - amount)}\n\n"
        f"<i>Не забудь вернуть кредит!</i>",
        reply_markup=get_admin_keyboard() if is_admin(user_id) else get_main_keyboard(),
        parse_mode="HTML"
    )
    context.user_data['awaiting_credit_take'] = False

async def show_admin_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("🚫 Доступ запрещён!")
        return
    
    users = db.get_all_users()
    pending_users = [(uid, data) for uid, data in users.items() if data.get('credit_pending', 0) > 0]
    
    if not pending_users:
        await query.edit_message_text("✅ <b>Нет заявок на рассмотрение</b>", parse_mode="HTML")
        return
    
    text = "📝 <b>Заявки на кредит</b>\n\n"
    keyboard = []
    
    for uid, data in pending_users:
        amount = data.get('credit_pending', 0)
        try:
            user = await context.bot.get_chat(int(uid))
            name = user.username or user.first_name or uid
        except:
            name = uid[:8]
        
        text += f"👤 @{name}\n"
        text += f"💰 Сумма: {amount} монет\n"
        text += f"🆔 ID: {uid}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✅ Одобрить @{name}", callback_data=f"approve_credit_{uid}_{amount}"),
            InlineKeyboardButton(f"❌ Отказать @{name}", callback_data=f"decline_credit_{uid}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 В банк", callback_data="go_bank")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_credit_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("🚫 Доступ запрещён!")
        return
    
    data = query.data
    
    if data.startswith("approve_credit_"):
        parts = data.replace("approve_credit_", "").split("_")
        target_id = parts[0]
        amount = int(parts[1])
        
        if amount > 20000:
            await query.edit_message_text("❌ Максимум 20,000 монет!")
            return
        
        target_data = db.get_user(target_id)
        target_data['credit_limit'] = target_data.get('credit_limit', 0) + amount
        target_data['credit_pending'] = 0
        db.update_user(target_id, target_data)
        
        await query.edit_message_text(
            f"✅ <b>Кредит одобрен!</b>\n\n"
            f"👤 Пользователь ID: {target_id}\n"
            f"💰 Сумма: {amount} монет\n"
            f"📊 Новый кредитный лимит: {format_num(target_data['credit_limit'])}\n\n"
            f"<i>Пользователь может взять кредит через кнопку 'Взять кредит'</i>",
            parse_mode="HTML"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"✅ <b>Кредит одобрен!</b>\n\n"
                     f"💰 Сумма: {amount} монет\n"
                     f"📊 Твой кредитный лимит: {format_num(target_data['credit_limit'])}\n\n"
                     f"<i>Теперь ты можешь взять кредит через банк.</i>",
                parse_mode="HTML"
            )
        except:
            pass
        
        return
    
    elif data.startswith("decline_credit_"):
        target_id = data.replace("decline_credit_", "")
        target_data = db.get_user(target_id)
        target_data['credit_pending'] = 0
        db.update_user(target_id, target_data)
        
        await query.edit_message_text(
            f"❌ <b>Кредит отклонён</b>\n\n"
            f"👤 Пользователь ID: {target_id}\n"
            f"<i>Пользователь уведомлён</i>",
            parse_mode="HTML"
        )
        
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text="❌ <b>Кредит отклонён</b>\n\nАдминистратор отклонил вашу заявку.",
                parse_mode="HTML"
            )
        except:
            pass
        
        return

# ============================================
# КОЛБЭКИ
# ============================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Магазин
    if data in ["buy_multi", "buy_auto", "buy_bonus", "back_shop"]:
        await shop_callback(update, context)
        return
    
    # NFT
    if data.startswith("buy_nft_"):
        await buy_nft(update, context)
    elif data == "my_nfts":
        await show_my_nfts(update, context)
    elif data == "sell_nft":
        await sell_nft_menu(update, context)
    elif data == "player_market":
        await player_market(update, context)
    elif data == "go_nft_market":
        await go_nft_market(update, context)
    elif data == "back_nft":
        await back_nft(update, context)
    elif data.startswith("set_sell_"):
        await set_sell_price(update, context)
    elif data.startswith("player_buy_"):
        await player_buy_nft(update, context)
    
    # Банк
    elif data == "credit_apply":
        await credit_apply(update, context)
    elif data == "credit_info":
        await credit_info(update, context)
    elif data == "credit_take":
        await credit_take(update, context)
    elif data == "transfer":
        await transfer_menu(update, context)
    elif data == "back_transfer":
        await go_bank(update, context)
    elif data == "admin_credits":
        await show_admin_credits(update, context)
    elif data == "go_bank":
        await go_bank(update, context)
    elif data == "back_bank":
        await back_bank(update, context)
    elif data.startswith("approve_credit_"):
        await handle_credit_admin(update, context)
    elif data.startswith("decline_credit_"):
        await handle_credit_admin(update, context)

async def go_nft_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📦 Мои NFT", callback_data="my_nfts")],
        [InlineKeyboardButton("💰 Продать NFT", callback_data="sell_nft")],
        [InlineKeyboardButton("🏪 Рынок игроков", callback_data="player_market")],
    ]
    
    all_nfts = db.get_nft_market()
    for nft_id, nft_data in NFT_COLLECTIONS.items():
        sold_count = sum(1 for n in all_nfts if n['collection_id'] == nft_id)
        available = nft_data['total'] - sold_count
        if available > 0:
            keyboard.append([InlineKeyboardButton(
                f"{nft_data['emoji']} {nft_data['name']} - {nft_data['price']}💰 ({available} шт.)",
                callback_data=f"buy_nft_{nft_id}"
            )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_nft")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    nfts = user_data.get('nft_inventory', [])
    
    await query.edit_message_text(
        f"🛒 <b>NFT Маркет</b>\n\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"📦 NFT в инвентаре: {len(nfts)}\n\n"
        f"<b>Доступные NFT:</b>\n"
        f"🐉 Дракон — Легендарный (+30% к силе) — 15000💰\n"
        f"💎 Кристалл — Редкий (+15% к силе) — 8000💰\n"
        f"👑 Корона — Мифический (+50% к силе) — 25000💰\n\n"
        f"<i>Выбери действие:</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def back_nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    await query.edit_message_text("🍐 <b>Pear Clicker</b>\n\nГлавное меню", reply_markup=keyboard, parse_mode="HTML")

async def go_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📝 Заявка на кредит", callback_data="credit_apply")],
        [InlineKeyboardButton("📊 Мои кредиты", callback_data="credit_info")],
        [InlineKeyboardButton("💳 Взять кредит", callback_data="credit_take")],
        [InlineKeyboardButton("💸 Перевод", callback_data="transfer")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_bank")],
    ]
    
    if is_admin(user_id):
        keyboard.insert(1, [InlineKeyboardButton("✅ Одобрить заявки", callback_data="admin_credits")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    available_credit = user_data.get('credit_limit', 0) - user_data.get('credit_used', 0)
    pending = user_data.get('credit_pending', 0)
    
    await query.edit_message_text(
        f"🏦 <b>Банк | Переводы</b>\n\n"
        f"💰 Баланс: {format_num(user_data['balance'])}\n"
        f"📊 Кредитный лимит: {format_num(user_data.get('credit_limit', 0))}\n"
        f"💳 Использовано: {format_num(user_data.get('credit_used', 0))}\n"
        f"💎 Доступно: {format_num(max(0, available_credit))}\n"
        f"⏳ Заявка: {format_num(pending) if pending > 0 else 'Нет'}\n"
        f"📈 Всего взято: {format_num(user_data.get('total_credit_taken', 0))}\n\n"
        f"<i>Максимальный кредит: 20,000 монет</i>\n"
        f"<i>Для перевода напиши: @username сумма</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def back_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
    await query.edit_message_text("🍐 <b>Pear Clicker</b>\n\nГлавное меню", reply_markup=keyboard, parse_mode="HTML")

# ============================================
# АДМИН-ПАНЕЛЬ
# ============================================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("🚫 Доступ только для админов!", parse_mode="HTML")
        return
    
    await update.message.reply_text(
        "⚙️ <b>Админ-панель</b>\n\n"
        "📝 Кредиты:\n✅ Нажми 'Одобрить заявки' в банке (макс 20,000)\n\n"
        "🎫 Промокоды:\n/promo награда использований — создать промокод\n\n"
        "📢 Рассылка:\n/broadcast текст — отправить всем\n\n"
        "👑 Команды:\n"
        "/addadmin @username — добавить админа\n"
        "/removeadmin @username — удалить админа\n"
        "/give @username сумма — выдать монеты\n"
        "/take @username сумма — забрать монеты\n"
        "/ban @username — забанить\n"
        "/unban @username — разбанить\n"
        "/warn @username — предупреждение\n"
        "/stats — статистика\n"
        "/reset @username — сбросить прогресс\n"
        "/setlevel @username уровень — установить уровень\n"
        "/setpower @username сила — установить силу\n"
        "/topadmin — топ с ID\n"
        "/resetnft — сбросить все NFT\n"
        "/approve user_id сумма — одобрить кредит\n"
        "/decline user_id — отклонить кредит",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# ============================================
# АДМИН-КОМАНДЫ
# ============================================

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != "cagalo": return
    if not context.args:
        await update.message.reply_text("❌ /addadmin @username")
        return
    target = context.args[0].replace('@', '')
    for uid in db.get_all_users().keys():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                if uid not in ADMINS:
                    ADMINS.append(uid)
                    db.save()
                    await update.message.reply_text(f"✅ @{target} добавлен!")
                else:
                    await update.message.reply_text(f"@{target} уже админ")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != "cagalo": return
    if not context.args:
        await update.message.reply_text("❌ /removeadmin @username")
        return
    target = context.args[0].replace('@', '')
    for uid in ADMINS:
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                ADMINS.remove(uid)
                db.save()
                await update.message.reply_text(f"✅ @{target} удалён!")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def give_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /give @username сумма")
        return
    target = context.args[0].replace('@', '')
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Сумма должна быть числом")
        return
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['balance'] = data.get('balance', 0) + amount
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} +{format_num(amount)} монет")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def take_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /take @username сумма")
        return
    target = context.args[0].replace('@', '')
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Сумма должна быть числом")
        return
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['balance'] = max(0, data.get('balance', 0) - amount)
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} -{format_num(amount)} монет")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ /ban @username")
        return
    target = context.args[0].replace('@', '')
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['banned'] = True
                db.update_user(uid, data)
                await update.message.reply_text(f"🚫 @{target} забанен!")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ /unban @username")
        return
    target = context.args[0].replace('@', '')
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['banned'] = False
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} разбанен!")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ /warn @username")
        return
    target = context.args[0].replace('@', '')
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['warns'] = data.get('warns', 0) + 1
                if data['warns'] >= 3:
                    data['banned'] = True
                    await update.message.reply_text(f"🚫 @{target} забанен за 3 предупреждения!")
                else:
                    await update.message.reply_text(f"⚠️ @{target} предупреждение ({data['warns']}/3)")
                db.update_user(uid, data)
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def stats_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = db.get_all_users()
    market = db.get_nft_market()
    promocodes = db.get_all_promocodes()
    
    total_nfts = len(market)
    nft_for_sale = sum(1 for n in market if n.get('for_sale', False))
    total_nft_value = sum(n.get('price', 0) for n in market if n.get('for_sale', False))
    
    total_credit_limit = sum(d.get('credit_limit', 0) for d in users.values())
    total_credit_used = sum(d.get('credit_used', 0) for d in users.values())
    
    await update.message.reply_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"💰 Всего монет: {format_num(sum(d.get('balance', 0) for d in users.values()))}\n"
        f"🖱️ Всего кликов: {format_num(sum(d.get('total_clicks', 0) for d in users.values()))}\n"
        f"👑 Админов: {len(ADMINS)}\n"
        f"📦 Всего NFT: {total_nfts}\n"
        f"💎 NFT на продаже: {nft_for_sale}\n"
        f"💰 Стоимость NFT: {format_num(total_nft_value)}\n"
        f"🏦 Кредитный лимит: {format_num(total_credit_limit)}\n"
        f"💳 Использовано кредитов: {format_num(total_credit_used)}\n"
        f"🎫 Промокодов: {len(promocodes)}",
        parse_mode="HTML"
    )

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ /reset @username")
        return
    target = context.args[0].replace('@', '')
    for uid in db.get_all_users().keys():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data = db.get_user(uid)
                for nft in db.get_nft_market():
                    if nft['owner_id'] == uid:
                        db.remove_nft_from_market(nft['id'])
                
                data['balance'] = 0
                data['click_power'] = 1
                data['level'] = 1
                data['xp'] = 0
                data['total_clicks'] = 0
                data['boosts'] = {'multi_click': 0, 'auto_clicker': 0, 'click_bonus': 0}
                data['nft_inventory'] = []
                data['credit_limit'] = 0
                data['credit_used'] = 0
                data['credit_pending'] = 0
                data['total_credit_taken'] = 0
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} сброшен!")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /setlevel @username уровень")
        return
    target = context.args[0].replace('@', '')
    try:
        level = int(context.args[1])
    except:
        await update.message.reply_text("❌ Уровень должен быть числом")
        return
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['level'] = level
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} уровень {level}")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def set_power(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /setpower @username сила")
        return
    target = context.args[0].replace('@', '')
    try:
        power = int(context.args[1])
    except:
        await update.message.reply_text("❌ Сила должна быть числом")
        return
    for uid, data in db.get_all_users().items():
        try:
            user = await context.bot.get_chat(int(uid))
            if user.username == target:
                data['click_power'] = power
                db.update_user(uid, data)
                await update.message.reply_text(f"✅ @{target} сила {power}")
                return
        except:
            continue
    await update.message.reply_text(f"❌ @{target} не найден")

async def top_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = db.get_all_users()
    sorted_users = sorted(
        [(uid, data.get('balance', 0), len(data.get('nft_inventory', []))) for uid, data in users.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    text = "🏆 <b>Топ с ID</b>\n\n"
    for i, (uid, balance, nft_count) in enumerate(sorted_users, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        try:
            user = await context.bot.get_chat(int(uid))
            name = user.username or user.first_name or str(uid)
        except:
            name = str(uid)[:8]
        text += f"{medal} {name} (ID: {uid}) — {format_num(balance)} 💰 📦{nft_count}\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def reset_nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != "cagalo":
        await update.message.reply_text("🚫 Доступ только для @cagalo!")
        return
    
    for user_id, data in db.get_all_users().items():
        data['nft_inventory'] = []
        db.update_user(user_id, data)
    
    db.nft_market = []
    db.save()
    
    await update.message.reply_text("✅ Все NFT сброшены!")

async def approve_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("❌ /approve user_id сумма")
        return
    
    target_id = context.args[0]
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Сумма должна быть числом")
        return
    
    if amount > 20000:
        await update.message.reply_text("❌ Максимум 20,000")
        return
    
    target_data = db.get_user(target_id)
    target_data['credit_limit'] = target_data.get('credit_limit', 0) + amount
    target_data['credit_pending'] = 0
    db.update_user(target_id, target_data)
    
    await update.message.reply_text(f"✅ Кредит {amount} монет выдан пользователю {target_id}")
    
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"✅ Кредит {amount}💰 одобрен! Новый лимит: {format_num(target_data['credit_limit'])}",
            parse_mode="HTML"
        )
    except:
        pass

async def decline_credit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("❌ /decline user_id")
        return
    
    target_id = context.args[0]
    target_data = db.get_user(target_id)
    target_data['credit_pending'] = 0
    db.update_user(target_id, target_data)
    
    await update.message.reply_text(f"❌ Кредит отклонён для {target_id}")
    
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text="❌ Кредит отклонён администратором."
        )
    except:
        pass

async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ только для админов!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: /promo награда количество_использований\nПример: /promo 500 10"
        )
        return
    
    try:
        reward = int(context.args[0])
        max_uses = int(context.args[1])
    except:
        await update.message.reply_text("❌ Награда и количество должны быть числами!")
        return
    
    if reward < 10:
        await update.message.reply_text("❌ Минимальная награда — 10 монет!")
        return
    if max_uses < 1 or max_uses > 100:
        await update.message.reply_text("❌ Количество использований от 1 до 100!")
        return
    
    code = generate_promocode()
    db.create_promocode(code, reward, max_uses)
    
    await update.message.reply_text(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎫 Код: <code>{code}</code>\n"
        f"💰 Награда: {reward} монет\n"
        f"📊 Использований: {max_uses}\n\n"
        f"<i>Отправь код игрокам!</i>",
        parse_mode="HTML"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📢 Рассылка всем игрокам"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("🚫 Доступ только для админов!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Использование:</b>\n\n"
            "/broadcast Текст сообщения\n\n"
            "<b>Пример:</b>\n"
            "/broadcast Привет! У нас новое обновление! 🎉",
            parse_mode="HTML"
        )
        return
    
    text = ' '.join(context.args)
    users = db.get_all_users()
    total = len(users)
    
    if total == 0:
        await update.message.reply_text("❌ Нет пользователей для рассылки!")
        return
    
    status_msg = await update.message.reply_text(
        f"📤 <b>Начинаю рассылку...</b>\n\n👥 Всего игроков: {total}",
        parse_mode="HTML"
    )
    
    success = 0
    failed = 0
    
    for uid in users.keys():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 <b>Объявление</b>\n\n{text}",
                parse_mode="HTML"
            )
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Не доставлено: {failed}\n"
        f"👥 Всего: {total}",
        parse_mode="HTML"
    )

# ============================================
# ЗАПУСК
# ============================================

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    
    # Админ-команды
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("give", give_money))
    application.add_handler(CommandHandler("take", take_money))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("stats", stats_bot))
    application.add_handler(CommandHandler("reset", reset_user))
    application.add_handler(CommandHandler("setlevel", set_level))
    application.add_handler(CommandHandler("setpower", set_power))
    application.add_handler(CommandHandler("topadmin", top_admin))
    application.add_handler(CommandHandler("resetnft", reset_nft))
    application.add_handler(CommandHandler("approve", approve_credit_command))
    application.add_handler(CommandHandler("decline", decline_credit_command))
    application.add_handler(CommandHandler("promo", promo_command))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    # Callback обработчики
    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^(buy_multi|buy_auto|buy_bonus|back_shop|buy_nft_|my_nfts|sell_nft|player_market|go_nft_market|back_nft|set_sell_|player_buy_|credit_|admin_credits|go_bank|back_bank|back_transfer|transfer|approve_credit_|decline_credit_)"))
    
    # Обработка сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🍐 Pear Clicker Бот запущен!")
    print(f"👑 Админы: {ADMINS}")
    print("💰 Магазин с инлайн-кнопками!")
    print("📊 Данные хранятся в JSON")
    
    application.run_polling()

if __name__ == "__main__":
    main()