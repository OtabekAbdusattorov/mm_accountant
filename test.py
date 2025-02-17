import telebot

# Replace with your bot's token
TOKEN = 'your_bot_token_here'

# Create a bot object
bot = telebot.TeleBot(TOKEN)

# Define a message handler for the '/start' command
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "Welcome to the bot!")

# Polling to keep the bot running
bot.polling()
