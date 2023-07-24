import random

import logging
import os
import csv

from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, KeyboardButton, \
    ReplyKeyboardMarkup, ReplyMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

import psycopg2

from collections import Counter
from loyverse import LoyverseConnector
from prompt_parser import parse

from itertools import groupby

from datetime import datetime, time, timedelta
import pytz

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('telegram_token')
LOYVERSE_TOKEN = os.getenv('loyverse_token')
BIRTHDAY_CHATS = set([int(chatid) for chatid in os.getenv('birthday_chats', '').split(',') if chatid])
BIRTHDAY_POINTS = os.getenv('birthday_points', 5)
TIMEZONE = pytz.timezone(os.getenv('timezone', 'Europe/Bucharest'))

# Loyverse connector
lc = LoyverseConnector(LOYVERSE_TOKEN)

# prompts
prompts = parse("resources/prompts.txt")
logging.info(prompts)

#sarcasm
with open("resources/donate_sarcasm.txt", "r") as file:
    donate_sarcastic_comments = file.readlines()

with open("resources/balance_sarcasm.txt", "r") as file:
    balance_sarcastic_comments = file.readlines()
# raffle 
raffle_register = []

# Birthday-list

with open("resources/birthday_messages.txt", "r") as file:
    birthday_messages = file.readlines()

# The keys are birthdays, the values are lists of users without @
birthdays = {}

# Open the CSV file
with open('resources/T5 Community Data_Birthdays.csv', 'r') as csvfile:
    # Create a CSV reader object
    reader = csv.DictReader(csvfile)

    birthday_data = [(f"{row['Month']}/{row['Day']}", row['Username']) for row in reader]
    sorted_birthdays = sorted(birthday_data, key=lambda row: row[0])
    for date, users in groupby(sorted_birthdays, key=lambda row: row[0]):
        birthdays[date] = [user[1] for user in users]

def is_convertible_to_number(s):
    try:
        float(s)  # or int(s) if you only want to check for integers
        return True
    except ValueError:
        return False


def remove_at_symbol(text):
    if text.startswith('@'):
        return text[1:]
    else:
        return text


def help(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=prompts.get("welcome"),
        parse_mode="MarkdownV2",
    )


def balance(update: Update, context: CallbackContext) -> None:
    username = update.message.from_user.username

    # Process the username and send a reply
    if username:
        try:
            user_balance = int(lc.get_balance(username))
            sarc = random.choice(balance_sarcastic_comments).rstrip('\n')
            reply_text = f"{sarc} @{username}, you have {user_balance} T5 Loyalty Points!"
        except Exception as e:
            reply_text = f"BeeDeeBeeBoop 🤖 Error : {e}"
    else:
        reply_text = "First, create a username in Telegram!"

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply_text,
    )


def donate(update: Update, context: CallbackContext) -> None:
    # Get the arguments passed with the command
    args = context.args

    # Process the arguments and send a reply
    if len(args) < 2:
        reply_text = f"respect the following format: /donate telegram_username number_of_points"
    elif not is_convertible_to_number(args[1]):
        reply_text = f"number_of_points must be ... a number 😬"
    else:
        username = update.message.from_user.username

        # Check if the donor and recipient usernames are the same
        recipient_username = remove_at_symbol(args[0])
        if recipient_username == username:
            reply_text = "Sorry, self-donations are not allowed."
        else:
            # Process the username and send a reply
            if username:
                try:
                    if lc.donate_points(username, recipient_username, float(args[1])):
                        sarc = random.choice(donate_sarcastic_comments).rstrip('\n')
                        reply_text = f"{sarc} @{username} donated {args[1]} points to {args[0]}"
                    else:
                        reply_text = "Error: failed to donate points"
                except Exception as e:
                    reply_text = str(e)
            else:
                reply_text = "First, create a username in Telegram!"

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply_text,
    )
def raffle(update: Update, context: CallbackContext) -> None:
    global raffle_register
    
    username = update.message.from_user.username

    # Process the username and send a reply
    if username:
        try:
            lc.remove_points(username, 5)
            raffle_register.append(username)
            entry_count = Counter(raffle_register)
            reply_text = f"Congrats @{username}. You just bought a ticket for the Community Raffle. Thanks for supporting and good luck!\n\n"

            # Display the list of entries with entry counts
            for entry, count in entry_count.items():
                reply_text += f"@{entry} - {count} Ticket(s)\n"
        except Exception as e:
            reply_text =str(e)
    else:
        reply_text = "First, create a username in Telegram!"

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply_text,
    )
    
# A command for god to edit the list for the raffle
def raffle_list(update: Update, context: CallbackContext) -> None:
  global raffle_register
    
  username = update.message.from_user.username
  if username == "roblevermusic":
    raffle_register = context.args

  print(raffle_register)


def send_birthdays(context: CallbackContext) -> None:
    if not BIRTHDAY_CHATS:
        return

    current_date = datetime.now()
    current_birthday = f"{current_date.month}/{current_date.day}"

    if current_birthday not in birthdays:
        return

    usernames = [f"@{user}" for user in birthdays[current_birthday]]

    if len(usernames) == 1:
        users_text = usernames[0]
    else:
        users_text = ', '.join(usernames[0:-1]) + ' and ' + usernames[-1]

    announcement = prompts.get('birthday_announcement').format(
        users=users_text,
        message=random.choice(birthday_messages).rstrip('\n'),
        points=BIRTHDAY_POINTS
    )

    for chat_id in BIRTHDAY_CHATS:
        context.bot.send_message(
            chat_id=chat_id,
            text=announcement,
        )

    for user in birthdays[current_birthday]:
        lc.add_points(user, BIRTHDAY_POINTS)


def start_announcing_birthdays(update: Update, context: CallbackContext) -> None:
    BIRTHDAY_CHATS.add(update.message.chat_id)

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="I will announce birthdays in this chat, every day at midnight.",
    )

def stop_announcing_birthdays(update: Update, context: CallbackContext) -> None:
    BIRTHDAY_CHATS.remove(update.message.chat_id)

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="I will no longer announce birthdays in this chat.",
    )


def main() -> None:
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("balance", balance))
    dispatcher.add_handler(CommandHandler("donate", donate))
    dispatcher.add_handler(CommandHandler("raffle", raffle))
    dispatcher.add_handler(CommandHandler("raffle_list", raffle_list)) 
    dispatcher.add_handler(CommandHandler("start_announcing_birthdays", start_announcing_birthdays))
    dispatcher.add_handler(CommandHandler("stop_announcing_birthdays", stop_announcing_birthdays))

    # Register the daily birthday job
    updater.job_queue.run_daily(send_birthdays, time(0, 0, 0, 0, TIMEZONE))

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()

