import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import os
from dotenv import load_dotenv
import json
import time


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

