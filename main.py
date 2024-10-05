import os
from openai import OpenAI
import telebot
import sqlite3
import dotenv

dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ORGANIZATION_ID = os.getenv('ORGANIZATION_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

client = OpenAI(api_key=OPENAI_API_KEY, organization=ORGANIZATION_ID)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

print('Bot initialized')

conn = sqlite3.connect('messages.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        fullname TEXT,
        message TEXT,
        chat TEXT
    )
''')
conn.commit()


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'To receive summary use /summary')


@bot.message_handler(commands=['summary'])
def handle_summary(message):
    try:
        if len(message.text.split()) != 2 or not message.text.split()[1].isdigit():
            bot.reply_to(message, "Usage: /summary [number of messages]")
            return

        num_messages = int(message.text.split()[1])
        if num_messages > 9223372036854775807:
            bot.reply_to(message, 'У тебя такой большой, я ливаю 🤯')
            return

        chat_id = message.chat.id
        cursor.execute('SELECT username, fullname, message FROM messages WHERE chat=? ORDER BY id DESC LIMIT ?',
                       (chat_id, num_messages))
        fetched_messages = cursor.fetchall()

        if not fetched_messages:
            bot.reply_to(message, "No messages found to summarize.")
            return
        fetched_messages.reverse()

        messages_to_summarize = "\n".join([f"[{fullname} {user}]: {msg}" for user, fullname, msg in fetched_messages])

        response = client.chat.completions.create(model="gpt-3.5-turbo",
                                                  messages=[
                                                      {"role": "system",
                                                       "content": "Сделай саммари следующего диалога:"},
                                                      {"role": "user", "content": messages_to_summarize},
                                                  ])
        summary = response.choices[0].message.content.strip()
        bot.reply_to(message, summary)

    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    try:
        user = message.from_user.username
        fullname = message.from_user.full_name
        text = message.text
        chat_id = message.chat.id
        cursor.execute('INSERT INTO messages (username, fullname, message, chat) VALUES (?, ?, ?, ?)',
                       (user, fullname, text, chat_id))
        conn.commit()
        print(f"Message from {user} stored successfully.")
    except Exception as e:
        print(f"Error occurred while storing message: {e}")


# Start the bot
bot.infinity_polling()
