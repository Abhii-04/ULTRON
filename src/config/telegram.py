import os 
from dotenv import load_dotenv
import telebot

load_dotenv()

telegram_api_key = os.getenv('TELEGRAM_BOT_API_KEY')
bot = telebot.TeleBot(telegram_api_key)


@bot.message_handler(commands=['start','hello'])
def send_welcome(message):
    bot.reply_to(message,"howdy,how are you doing?")

@bot.message_handler(func=lambda msg:True)
def chatting(message):
    bot.reply_to(message,message.text)

bot.infinity_polling()