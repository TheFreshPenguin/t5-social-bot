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

from datetime import datetime, time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# telegram token
if os.environ.get('is_prod') == 'True':
    TELEGRAM_TOKEN = os.environ['telegram_token']
    LOYVERSE_TOKEN = os.environ['loyverse_token']
else:
    with open('secret.txt', 'r') as file:
        TELEGRAM_TOKEN = file.read()

    with open('lv_secret.txt', 'r') as file:
        LOYVERSE_TOKEN = file.read()

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

birthdays = {}

# Open the CSV file
with open('resources/T5 Community Data_Birthdays.csv', 'r') as csvfile:
    # Create a CSV reader object
    reader = csv.DictReader(csvfile)
    
    # Process each row
    for row in reader:
        username = row['Username']
        month = int(row['Month'])
        day = int(row['Day'])
        
        # Do something with the data (e.g., store it in a data structure, print it, etc.)
        # print(f"{Username}'s birthday is on {month}/{day}.")
        birthdays[username] = f"{month}/{day}"

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

def birthday(update: Update, context: CallbackContext) -> None:
    birthday_of_today = []
    
    current_date = datetime.now()

    current_month = current_date.month
    current_day = current_date.day
    for key, value in birthdays.items():
        if value == f"{current_month}/{current_day}":
            birthday_of_today.append(key)
    
    context.bot.send_message(
        chat_id=-961065253,
        text=str(birthday_of_today),
    )

    
def main() -> None:
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher
    j = updater.job_queue

    # Register commands
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("balance", balance))
    dispatcher.add_handler(CommandHandler("donate", donate))
    dispatcher.add_handler(CommandHandler("raffle", raffle))
    dispatcher.add_handler(CommandHandler("raffle_list", raffle_list)) 
    #dispatcher.add_handler(CommandHandler("birthday", birthday)) 
    j.run_daily(birthday, time(13, 8), context=None, name=None)

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()


