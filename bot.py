import telebot
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


@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = MESSAGES.get('start_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def send_help(message):
    text = MESSAGES.get('help_message', 'Сообщение не найдено')
    bot.reply_to(message, text, parse_mode='Markdown')

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
