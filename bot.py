import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import os
from dotenv import load_dotenv
import json
import time


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден, проверьте .env")

def load_messages():
    try:
        with open('data/messages.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("message.json не найден")
        return {}
    except json.JSONDecodeError:
        print("Ошибка в формате messages.json")
        return {}

MESSAGES = load_messages()

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def calculate_credit_payment(debt, annual_rate, months):
    """
    Расчет ежемесячного платежа по аннуитетной схеме
    debt - сумма долга
    annual_rate - годовая процентная ставка
    months - срок в месяцах
    """
    monthly_rate = annual_rate / 100 / 12  # Месячная ставка
    coefficient = (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    monthly_payment = debt * coefficient
    total_payment = monthly_payment * months
    overpayment = total_payment - debt
    
    return {
        'monthly_payment': round(monthly_payment, 2),
        'total_payment': round(total_payment, 2),
        'overpayment': round(overpayment, 2),
        'debt': debt,
        'annual_rate': annual_rate,
        'months': months
    }


@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = MESSAGES.get('start_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    text = MESSAGES.get('help_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')


# Обработчик команды /creditcard
@bot.message_handler(commands=['creditcard'])
def start_credit_calculation(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'step': 'waiting_debt'}
    
    text = MESSAGES.get('creditcard_welcome', 'Введите сумму долга:')
    bot.send_message(chat_id, text, parse_mode='Markdown')

# Обработчик ввода суммы долга
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('step') == 'waiting_debt')
def handle_debt_input(message):
    chat_id = message.chat.id
    
    try:
        debt = float(message.text.replace(',', '.').replace(' ', ''))
        if debt <= 0:
            bot.send_message(chat_id, "❌ Сумма долга должна быть положительной!")
            return
        
        user_data[chat_id]['debt'] = debt
        user_data[chat_id]['step'] = 'waiting_interest'
        
        text = MESSAGES.get('creditcard_interest', 'Введите процентную ставку:')
        
        # Создаем клавиатуру с кнопками процентов
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn30 = types.KeyboardButton('30%')
        btn40 = types.KeyboardButton('40%')
        btn50 = types.KeyboardButton('50%')
        btn60 = types.KeyboardButton('60%')
        markup.add(btn30, btn40, btn50, btn60)
        
        bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректную сумму (например: 50000 или 50.000)")

# Обработчик ввода процентной ставки
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('step') == 'waiting_interest')
def handle_interest_input(message):
    chat_id = message.chat.id
    
    try:
        # Убираем символ % если есть и преобразуем в число
        interest_text = message.text.replace('%', '').replace(',', '.').strip()
        interest = float(interest_text)
        
        if interest <= 0:
            bot.send_message(chat_id, "❌ Процентная ставка должна быть положительной!")
            return
        
        user_data[chat_id]['interest'] = interest
        user_data[chat_id]['step'] = 'waiting_months'
        
        text = MESSAGES.get('creditcard_months', 'Выберите срок погашения:')
        
        # Создаем клавиатуру с кнопками сроков
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn6 = types.KeyboardButton('6 месяцев')
        btn12 = types.KeyboardButton('12 месяцев')
        btn18 = types.KeyboardButton('18 месяцев')
        btn24 = types.KeyboardButton('24 месяца')
        markup.add(btn6, btn12, btn18, btn24)
        
        bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=markup)
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректную процентную ставку (например: 40 или 40%)")

# Обработчик ввода срока погашения
@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get('step') == 'waiting_months')
def handle_months_input(message):
    chat_id = message.chat.id
    
    try:
        # Извлекаем число из текста (например: "12 месяцев" -> 12)
        months_text = message.text
        months = int(''.join(filter(str.isdigit, months_text)))
        
        if months <= 0:
            bot.send_message(chat_id, "❌ Срок должен быть положительным!")
            return
        
        # Получаем данные пользователя
        debt = user_data[chat_id]['debt']
        interest = user_data[chat_id]['interest']
        
        # Производим расчет
        result = calculate_credit_payment(debt, interest, months)
        
        # Форматируем результат
        response = f"""
💳 *Результат расчета:*

📊 *Исходные данные:*
• Сумма долга: {result['debt']:,.0f} ₽
• Годовая ставка: {result['annual_rate']}%
• Срок погашения: {result['months']} месяцев

💰 *Результаты:*
• 📅 Ежемесячный платеж: *{result['monthly_payment']:,.0f} ₽*
• 💵 Общая переплата: *{result['overpayment']:,.0f} ₽*
• 💰 Всего к оплате: *{result['total_payment']:,.0f} ₽*

💡 *Совет:* Старайтесь погашать кредитку досрочно, чтобы уменьшить переплату!
        """.replace(',', ' ')  # Убираем запятые для лучшего отображения
        
        # Убираем клавиатуру
        remove_markup = types.ReplyKeyboardRemove()
        
        bot.send_message(chat_id, response, parse_mode='Markdown', reply_markup=remove_markup)
        
        # Очищаем данные пользователя
        del user_data[chat_id]
        
    except ValueError:
        bot.send_message(chat_id, "❌ Пожалуйста, введите корректный срок (например: 12 или '12 месяцев')")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = MESSAGES.get('echo_all_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

if __name__ == '__main__':
    print("Successfully started")
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print(f'Error: {e}')
