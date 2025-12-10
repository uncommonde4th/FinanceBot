import os
import json
import telebot
import os
import json
import telebot
from dotenv import load_dotenv
from telebot import types

# ЗАГРУЗКА ПЕРЕМЕННЫХ ДЛЯ DOCKER
load_dotenv()

# Получаем токен
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверьте .env файл")

# Импортируем БАЗУ ДАННЫХ ПОСЛЕ загрузки .env
from database import Database

# Конфиг для Docker
def get_config():
    return {
        'debug': os.getenv('DEBUG', 'False').lower() == 'true',
        'web_app_url': os.getenv('WEB_APP_URL', 'https://your-domain.com'),
        'db_path': 'data/finance_bot.db'
    }

config = get_config()

# Загружаем сообщения
def load_messages():
    messages_path = 'data/messages.json'
    
    # Если файла нет - создаем минимальный
    default_messages = {
        'start_message': '👋 Добро пожаловать!',
        'help_message': '❓ Доступные команды...',
        'profile_empty': '📭 Нет активных кредитов'
    }
    
    try:
        with open(messages_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Файл {messages_path} не найден. Создаю минимальный...")
        os.makedirs('data', exist_ok=True)
        with open(messages_path, 'w', encoding='utf-8') as f:
            json.dump(default_messages, f, ensure_ascii=False, indent=2)
        return default_messages
    except json.JSONDecodeError:
        print(f"❌ Ошибка в {messages_path}. Использую значения по умолчанию")
        return default_messages

MESSAGES = load_messages()

# Создаем экземпляры
bot = telebot.TeleBot(BOT_TOKEN)
db = Database(config['db_path'])  # Передаем путь из конфига
user_data = {}

# Функция для расчета аннуитетного платежа
def calculate_credit_payment(debt, annual_rate, months):
    monthly_rate = annual_rate / 100 / 12
    coefficient = (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    monthly_payment = debt * coefficient
    total_payment = monthly_payment * months
    overpayment = total_payment - debt
    
    return {
        'monthly_payment': round(monthly_payment, 2),
        'total_payment': round(total_payment, 2),
        'overpayment': round(overpayment, 2)
    }

# Функция для расчета распределения платежа
def calculate_payment_distribution(current_debt, annual_rate, payment_amount):
    monthly_rate = annual_rate / 100 / 12
    interest_amount = current_debt * monthly_rate
    interest_amount = round(interest_amount, 2)
    
    if payment_amount >= interest_amount:
        principal_amount = payment_amount - interest_amount
        principal_amount = round(principal_amount, 2)
        remaining_debt = current_debt - principal_amount
        remaining_debt = max(0, round(remaining_debt, 2))
    else:
        principal_amount = 0
        remaining_debt = current_debt - payment_amount + interest_amount
        remaining_debt = round(remaining_debt, 2)
    
    return {
        'interest_amount': interest_amount,
        'principal_amount': principal_amount,
        'remaining_debt': remaining_debt
    }

# Функция для создания клавиатуры профиля
def create_profile_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add_credit = types.InlineKeyboardButton('💳 Добавить кредит', callback_data='add_credit')
    btn_make_payment = types.InlineKeyboardButton('💰 Платеж по кредиту', callback_data='make_payment')
    btn_edit = types.InlineKeyboardButton('✏️ Изменить', callback_data='edit_menu')
    btn_add_investment = types.InlineKeyboardButton('📈 Добавить вклад', callback_data='add_investment')
    markup.add(btn_add_credit, btn_make_payment, btn_edit, btn_add_investment)
    return markup

def create_edit_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_delete_credit = types.InlineKeyboardButton('🗑️ Удалить кредит', callback_data='delete_credit_menu')
    btn_delete_investment = types.InlineKeyboardButton('🗑️ Удалить вклад', callback_data='delete_investment_menu')
    btn_back = types.InlineKeyboardButton('🔙 Назад к профилю', callback_data='back_to_profile')
    markup.add(btn_delete_credit, btn_delete_investment, btn_back)
    return markup

def create_delete_credits_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    user_credits = db.get_user_credits(user_id)
    
    for credit in user_credits:
        credit_id, _, debt, current_debt, rate, months, months_paid, monthly_pay, _, _, created_at = credit
        btn_text = f"💳 {debt:,.0f}₽ под {rate}% ({current_debt:,.0f}₽ осталось)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'delete_credit_{credit_id}'))
    
    if not user_credits:
        markup.add(types.InlineKeyboardButton('❌ Нет кредитов для удаления', callback_data='no_credits'))
    
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_edit_menu'))
    return markup

# Функция для создания клавиатуры выбора кредита
def create_credits_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    user_credits = db.get_user_credits(user_id)
    
    for credit in user_credits:
        credit_id, _, debt, current_debt, rate, months, months_paid, monthly_pay, _, _, created_at = credit
        btn_text = f"💳 {debt:,.0f}₽ под {rate}% ({current_debt:,.0f}₽ осталось)"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'select_credit_{credit_id}'))
    
    if not user_credits:
        markup.add(types.InlineKeyboardButton('❌ Нет активных кредитов', callback_data='no_credits'))
    
    markup.add(types.InlineKeyboardButton('🔙 Назад к профилю', callback_data='back_to_profile'))
    return markup

# Функция для создания клавиатуры суммы платежа
def create_payment_keyboard(monthly_payment, current_debt):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    # Быстрые кнопки с рекомендуемыми суммами (ИСПРАВЛЕНО форматирование)
    btn_minimum = types.KeyboardButton(f'{monthly_payment:,.0f}'.replace(',', ' ') + ' ₽')
    btn_half = types.KeyboardButton(f'{monthly_payment * 1.5:,.0f}'.replace(',', ' ') + ' ₽')
    btn_double = types.KeyboardButton(f'{monthly_payment * 2:,.0f}'.replace(',', ' ') + ' ₽')
    btn_full = types.KeyboardButton(f'{current_debt:,.0f}'.replace(',', ' ') + ' ₽')
    
    markup.add(btn_minimum, btn_half, btn_double, btn_full)
    return markup
# Функция для отображения профиля пользователя
def show_user_profile(chat_id, user_id, message_id=None):
    user_credits = db.get_user_credits(user_id)
    username = bot.get_chat(user_id).username
    display_name = f"@{username}" if username else f"{bot.get_chat(user_id).first_name or 'Пользователь'}"
    
    if user_credits:
        credits_info = ""
        total_monthly_payment = 0
        total_current_debt = 0
        
        for credit in user_credits:
            credit_id, _, initial_debt, current_debt, rate, total_months, months_paid, monthly_pay, total_pay, overpay, created_at = credit
            
            # Расчет распределения следующего платежа
            next_payment = calculate_payment_distribution(current_debt, rate, monthly_pay)
            remaining_months = total_months - months_paid
            
            credits_info += f"""
💳 *Кредит {initial_debt:,.0f} ₽ под {rate}%*
• Текущий долг: {current_debt:,.0f} ₽
• Платеж: {monthly_pay:,.0f} ₽/мес
• Из них: 
  ├ Проценты: ~{next_payment['interest_amount']:,.0f} ₽
  └ Основной долг: ~{next_payment['principal_amount']:,.0f} ₽
• Осталось месяцев: {remaining_months}
• Оплачено: {months_paid} из {total_months} месяцев
"""
            total_monthly_payment += monthly_pay
            total_current_debt += current_debt
        
        credits_summary = f"📊 Всего кредитов: {len(user_credits)}\n💵 Общий долг: {total_current_debt:,.0f} ₽\n📅 Сумма платежей: {total_monthly_payment:,.0f} ₽/мес\n{credits_info}"
        
        profile_text = MESSAGES.get('profile_with_data', '').format(
            username=display_name,
            credits_info=credits_summary
        )
    else:
        profile_text = MESSAGES.get('profile_empty', '').format(username=display_name)
    
    keyboard = create_profile_keyboard()
    
    if message_id:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=profile_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    else:
        bot.send_message(
            chat_id,
            profile_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Регистрируем пользователя
    db.get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Устанавливаем кнопку меню для этого чата
#    menu_button = types.MenuButtonWebApp(
#        type="web_app",  # ← ДОБАВЬТЕ ЭТУ СТРОЧКУ
#        text="📱 Финансы",
#        web_app=types.WebAppInfo(url=web_app_url)
#    )
    
    try:
        bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=menu_button
        )
    except Exception as e:
        print(f"⚠️ Не удалось установить кнопку меню для {chat_id}: {e}")
    
    # Отправляем приветственное сообщение с кнопкой
#    markup = types.InlineKeyboardMarkup()
#    web_app_btn = types.InlineKeyboardButton(
#        "🚀 Открыть приложение", 
#        web_app=types.WebAppInfo(url=web_app_url)
#    )
#    markup.add(web_app_btn)
    
#    welcome_text = MESSAGES.get('start_message', 'Сообщение не найдено') + "\n\n💡 *Используйте кнопку меню слева внизу для быстрого доступа к приложению!*"
    
    bot.send_message(
        chat_id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    text = MESSAGES.get('start_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

# Обработчик команды /profile
@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    db.get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    show_user_profile(chat_id, user_id)

# Обработчик нажатий на inline кнопки
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    if call.data == 'add_credit':
        user_data[user_id] = {
            'step': 'waiting_credit_debt',
            'profile_message_id': message_id
        }
        
        text = "💳 *Добавление нового кредита*\n\nВведите сумму кредита:"
        bot.send_message(chat_id, text, parse_mode='Markdown')
        
    elif call.data == 'make_payment':
        # Показываем список кредитов для платежа
        user_credits = db.get_user_credits(user_id)
        if not user_credits:
            bot.answer_callback_query(call.id, "❌ У вас нет активных кредитов!")
            return
        
        text = MESSAGES.get('select_credit_for_payment', 'Выберите кредит:')
        keyboard = create_credits_keyboard(user_id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif call.data.startswith('select_credit_'):
        credit_id = int(call.data.split('_')[2])
        credit = db.get_credit_by_id(credit_id, user_id)
        
        if credit:
            credit_id, _, initial_debt, current_debt, rate, months, months_paid, monthly_pay, total_pay, overpay, created_at = credit
            
            user_data[user_id] = {
                'step': 'waiting_payment_amount',
                'selected_credit_id': credit_id,
                'current_debt': current_debt,
                'monthly_payment': monthly_pay,
                'annual_rate': rate,
                'profile_message_id': message_id
            }
            
            text = MESSAGES.get('enter_payment_amount', '').format(
                current_debt=current_debt,
                monthly_payment=monthly_pay
            )
            
            keyboard = create_payment_keyboard(monthly_pay, current_debt)
            bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=keyboard)
        else:
            bot.answer_callback_query(call.id, "❌ Кредит не найден!")
            
    elif call.data == 'edit_menu':
        # Меню редактирования
        text = "✏️ *Что вы хотите изменить?*"
        keyboard = create_edit_menu_keyboard()
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif call.data == 'delete_credit_menu':
        # Выбор кредита для удаления
        user_credits = db.get_user_credits(user_id)
        if not user_credits:
            bot.answer_callback_query(call.id, "❌ У вас нет кредитов для удаления!")
            return
            
        text = "🗑️ *Выберите кредит для удаления:*"
        keyboard = create_delete_credits_keyboard(user_id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif call.data.startswith('delete_credit_'):
        # Удаление выбранного кредита
        credit_id = int(call.data.split('_')[2])
        credit = db.get_credit_by_id(credit_id, user_id)
        
        if credit:
            success = db.delete_credit(credit_id, user_id)
            if success:
                bot.answer_callback_query(call.id, "✅ Кредит успешно удален!")
                show_user_profile(chat_id, user_id, message_id)
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка при удалении кредита!")
        else:
            bot.answer_callback_query(call.id, "❌ Кредит не найден!")
            
    elif call.data == 'delete_investment_menu':
        # Заглушка для вкладов
        bot.answer_callback_query(call.id, "💰 Функция удаления вкладов скоро будет доступна!")
        
    elif call.data == 'back_to_edit_menu':
        # Возврат в меню редактирования
        text = "✏️ *Что вы хотите изменить?*"
        keyboard = create_edit_menu_keyboard()
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif call.data == 'back_to_profile':
        show_user_profile(chat_id, user_id, message_id)
        
    elif call.data == 'add_investment':
        bot.answer_callback_query(call.id, "📈 Функция вкладов скоро будет доступна!")
        
    elif call.data == 'no_credits':
        bot.answer_callback_query(call.id, "❌ Нет доступных кредитов!")
# Обработчик ввода суммы платежа
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('step') == 'waiting_payment_amount')
def handle_payment_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        # ИСПРАВЛЕННОЕ извлечение числа - учитываем запятые как разделители тысяч
        payment_text = message.text.replace('₽', '').replace(' ', '').strip()
        
        # Заменяем запятые на точки для дробных чисел, но сохраняем запятые как разделители тысяч
        if '.' in payment_text:
            # Если есть точка, считаем что это десятичный разделитель
            payment_amount = float(payment_text.replace(',', ''))
        else:
            # Если нет точки, убираем запятые и преобразуем
            payment_amount = float(payment_text.replace(',', '.'))
        
        if payment_amount <= 0:
            bot.send_message(chat_id, "❌ Сумма платежа должна быть положительной!")
            return
        
        # Остальной код без изменений...
        user_data_entry = user_data[user_id]
        current_debt = user_data_entry['current_debt']
        monthly_payment = user_data_entry['monthly_payment']
        annual_rate = user_data_entry['annual_rate']
        credit_id = user_data_entry['selected_credit_id']
        profile_message_id = user_data_entry['profile_message_id']
        
        if payment_amount > current_debt + (current_debt * annual_rate / 100 / 12):
            bot.send_message(chat_id, "❌ Сумма платежа слишком большая!")
            return
        
        # Расчет распределения платежа
        distribution = calculate_payment_distribution(current_debt, annual_rate, payment_amount)
        
        # Сохраняем платеж в базу
        db.add_payment(
            credit_id=credit_id,
            user_id=user_id,
            payment_amount=payment_amount,
            principal_amount=distribution['principal_amount'],
            interest_amount=distribution['interest_amount'],
            remaining_debt=distribution['remaining_debt']
        )
        
        # Показываем результат
        response = MESSAGES.get('payment_success', '').format(
            payment_amount=payment_amount,
            interest_amount=distribution['interest_amount'],
            principal_amount=distribution['principal_amount'],
            remaining_debt=distribution['remaining_debt']
        )
        
        # Убираем клавиатуру
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, response, parse_mode='Markdown', reply_markup=remove_markup)
        
        # Обновляем профиль
        show_user_profile(chat_id, user_id, profile_message_id)
        
        # Очищаем временные данные
        del user_data[user_id]
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректную сумму (например: 5000, 5.000 или 5,000)")# [Остальные обработчики остаются без изменений - add_credit, help, finance, etc.]

# Обработчик ввода суммы кредита
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('step') == 'waiting_credit_debt')
def handle_credit_debt_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        debt = float(message.text.replace(',', '.').replace(' ', ''))
        if debt <= 0:
            bot.send_message(chat_id, "❌ Сумма кредита должна быть положительной!")
            return
        
        user_data[user_id]['debt'] = debt
        user_data[user_id]['step'] = 'waiting_credit_interest'
        
        text = "📊 Введите годовую процентную ставку (%):"
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn30 = types.KeyboardButton('30%')
        btn40 = types.KeyboardButton('40%')
        btn50 = types.KeyboardButton('50%')
        btn60 = types.KeyboardButton('60%')
        markup.add(btn30, btn40, btn50, btn60)
        
        bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректную сумму")

# Обработчик ввода процентной ставки для кредита
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('step') == 'waiting_credit_interest')
def handle_credit_interest_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        interest_text = message.text.replace('%', '').replace(',', '.').strip()
        interest = float(interest_text)
        
        if interest <= 0:
            bot.send_message(chat_id, "❌ Процентная ставка должна быть положительной!")
            return
        
        user_data[user_id]['interest'] = interest
        user_data[user_id]['step'] = 'waiting_credit_months'
        
        text = "⏱️ Выберите срок погашения (в месяцах):"
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn6 = types.KeyboardButton('6 месяцев')
        btn12 = types.KeyboardButton('12 месяцев')
        btn18 = types.KeyboardButton('18 месяцев')
        btn24 = types.KeyboardButton('24 месяца')
        markup.add(btn6, btn12, btn18, btn24)
        
        bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректную процентную ставку")

# Обработчик ввода срока погашения кредита
@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get('step') == 'waiting_credit_months')
def handle_credit_months_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        months_text = message.text
        months = int(''.join(filter(str.isdigit, months_text)))
        
        if months <= 0:
            bot.send_message(chat_id, "❌ Срок должен быть положительным!")
            return
        
        debt = user_data[user_id]['debt']
        interest = user_data[user_id]['interest']
        profile_message_id = user_data[user_id]['profile_message_id']
        
        result = calculate_credit_payment(debt, interest, months)
        
        # Сохраняем кредит в базу данных
        db.add_credit(
            user_id=user_id,
            debt_amount=debt,
            annual_rate=interest,
            months=months,
            monthly_payment=result['monthly_payment'],
            total_payment=result['total_payment'],
            overpayment=result['overpayment']
        )
        
        response = f"""
✅ *Кредит успешно добавлен!*

📊 *Данные кредита:*
• Сумма: {debt:,.0f} ₽
• Ставка: {interest}%
• Срок: {months} месяцев
• Ежемесячный платеж: *{result['monthly_payment']:,.0f} ₽*
• Переплата: *{result['overpayment']:,.0f} ₽*
        """.replace(',', ' ')
        
        remove_markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, response, parse_mode='Markdown', reply_markup=remove_markup)
        
        # Обновляем профиль
        show_user_profile(chat_id, user_id, profile_message_id)
        
        del user_data[user_id]
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректный срок")

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def send_help(message):
    text = MESSAGES.get('help_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

# Обработчик команды /finance
@bot.message_handler(commands=['finance'])
def send_finance_commands(message):
    text = MESSAGES.get('finance_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

# Обработчик обычных текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if user_id not in user_data:
        bot.reply_to(message, "🤔 Используйте /help для списка команд или /profile для просмотра вашего профиля")

# Обработчик команды /app
@bot.message_handler(commands=['app'])
def send_mini_app(message):
    markup = types.InlineKeyboardMarkup()
#    web_app_btn = types.InlineKeyboardButton(
#        "📱 Открыть финансовое приложение", 
#        web_app=types.WebAppInfo(url=web_app_url)
#    )
#    markup.add(web_app_btn)
    
#    bot.send_message(
#        message.chat.id,
#        "💫 *Откройте финансовое приложение для удобного управления:*",
#        parse_mode='Markdown',
##        reply_markup=markup
#    )


# Запуск бота
if __name__ == '__main__':
    print("✅ Бот запущен и готов к работе!")
    
    # Установка меню команд
    bot.set_my_commands([
        types.BotCommand("start", "🚀 Начало работы"),
        types.BotCommand("profile", "📊 Мой профиль"),
#       types.BotCommand("app", "📱 Веб-приложение"),
        types.BotCommand("help", "❓ Помощь")
    ])
    
    # Установка кнопки меню для Mini App
#    menu_button = types.MenuButtonWebApp(
#       type="web_app",  # ← ДОБАВЬТЕ ЭТУ СТРОЧКУ
#       text="📱 Финансы",
#       web_app=types.WebAppInfo(url=web_app_url)
#    )
    
    try:
        bot.set_chat_menu_button(menu_button=menu_button)
        print("✅ Кнопка меню установлена!")
    except Exception as e:
        print(f"⚠️ Не удалось установить кнопку меню: {e}")
    
    print("⏳ Ожидаем сообщения...")
    
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()
