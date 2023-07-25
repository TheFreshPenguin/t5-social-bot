from collections import Counter

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from helpers.loyverse import LoyverseConnector


class RaffleModule:
    def __init__(self, lc: LoyverseConnector):
        self.lc = lc
        self.entries = []

    def install(self, updater: Updater) -> None:
        updater.dispatcher.add_handler(CommandHandler("raffle", self.__raffle))
        updater.dispatcher.add_handler(CommandHandler("raffle_list", self.__raffle_list))

    def __raffle(self, update: Update, context: CallbackContext) -> None:
        username = update.message.from_user.username

        # Process the username and send a reply
        if username:
            try:
                self.lc.remove_points(username, 5)
                self.entries.append(username)
                entry_count = Counter(self.entries)
                reply_text = f"Congrats @{username}. You just bought a ticket for the Community Raffle. Thanks for supporting and good luck!\n\n"

                # Display the list of entries with entry counts
                for entry, count in entry_count.items():
                    reply_text += f"@{entry} - {count} Ticket(s)\n"
            except Exception as e:
                reply_text = str(e)
        else:
            reply_text = "First, create a username in Telegram!"

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=reply_text,
        )

    # A command for god to edit the list for the raffle
    def __raffle_list(self, update: Update, context: CallbackContext) -> None:
        username = update.message.from_user.username
        if username == "roblevermusic":
            self.entries = context.args

        print(self.entries)
