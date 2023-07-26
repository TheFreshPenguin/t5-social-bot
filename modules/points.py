import random

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from helpers.access_checker import AccessChecker
from helpers.loyverse import LoyverseConnector

# sarcasm
with open("resources/points_donate_sarcasm.txt", "r") as file:
    donate_sarcastic_comments = [line.rstrip('\n') for line in file.readlines()]

with open("resources/points_balance_sarcasm.txt", "r") as file:
    balance_sarcastic_comments = [line.rstrip('\n') for line in file.readlines()]


def _is_convertible_to_number(s):
    try:
        float(s)  # or int(s) if you only want to check for integers
        return True
    except ValueError:
        return False


def _remove_at_symbol(text):
    if text.startswith('@'):
        return text[1:]
    else:
        return text


class PointsModule:
    def __init__(self, lc: LoyverseConnector, ac: AccessChecker):
        self.lc = lc
        self.ac = ac

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("balance", self.__balance))
        application.add_handler(CommandHandler("donate", self.__donate))

    async def __balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        username = update.message.from_user.username

        # Process the username and send a reply
        if username:
            try:
                user_balance = int(self.lc.get_balance(username))
                sarc = random.choice(balance_sarcastic_comments)
                reply_text = f"{sarc} @{username}, you have {user_balance} T5 Loyalty Points!"
            except Exception as e:
                reply_text = f"BeeDeeBeeBoop 🤖 Error : {e}"
        else:
            reply_text = "First, create a username in Telegram!"

        await update.message.reply_text(reply_text)

    async def __donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Get the arguments passed with the command
        args = context.args

        # Process the arguments and send a reply
        if len(args) < 2:
            reply_text = f"respect the following format: /donate telegram_username number_of_points"
        elif not _is_convertible_to_number(args[1]):
            reply_text = f"number_of_points must be ... a number 😬"
        else:
            username = update.message.from_user.username

            # Check if the donor and recipient usernames are the same
            recipient_username = _remove_at_symbol(args[0])
            if recipient_username == username:
                reply_text = "Sorry, self-donations are not allowed."
            else:
                # Process the username and send a reply
                if username:
                    try:
                        if self.ac.can_donate_for_free(username):
                            successful = self.lc.add_points(recipient_username, float(args[1]))
                        else:
                            successful = self.lc.donate_points(username, recipient_username, float(args[1]))

                        if successful:
                            sarc = random.choice(donate_sarcastic_comments).rstrip('\n')
                            reply_text = f"{sarc} @{username} donated {args[1]} points to {args[0]}"
                        else:
                            reply_text = "Error: failed to donate points"
                    except Exception as e:
                        reply_text = str(e)
                else:
                    reply_text = "First, create a username in Telegram!"

        await update.message.reply_text(reply_text)
