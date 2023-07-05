import random

import logging
import os

from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, KeyboardButton, \
    ReplyKeyboardMarkup, ReplyMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

import psycopg2

from loyverse import LoyverseConnector
from prompt_parser import parse

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# telegram token
if os.environ.get('is_prod') == 'True':
    TELEGRAM_TOKEN = os.environ['telegram_token']
    DATABASE_URL = os.environ['DATABASE_URL']
    LOYVERSE_TOKEN = os.environ['loyverse_token']
else:
    with open('secret.txt', 'r') as file:
        TELEGRAM_TOKEN = file.read()

    with open('db_secret.txt', 'r') as file:
        DATABASE_URL = file.read()

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
            reply_text = f"{sarc}@{username}, you have {user_balance} T5 Loyalty Points!"
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

        # Process the username and send a reply
        if username:
            try:
                if lc.donate_points(username, remove_at_symbol(args[0]), float(args[1])):
                    sarc = random.choice(donate_sarcastic_comments)
                    reply_text = f"BeeDeeBeeBoop 🤖 {sarc}@{username}, you donated {args[1]} points to {args[0]}"
                else:
                    reply_text = f"BeeDeeBeeBoop 🤖 Error : failed to donate points"
            except Exception as e:
                reply_text = f"BeeDeeBeeBoop 🤖 Error : {e}"
        else:
            reply_text = "First, create a username in Telegram!"

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=reply_text,
    )


def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("balance", balance))
    dispatcher.add_handler(CommandHandler("donate", donate))

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
