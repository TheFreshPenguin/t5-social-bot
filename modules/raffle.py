from collections import Counter

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from helpers.access_checker import AccessChecker
from helpers.loyverse import LoyverseConnector


class RaffleModule:
    def __init__(self, lc: LoyverseConnector, ac: AccessChecker):
        self.lc = lc
        self.ac = ac
        self.entries = []

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("raffle", self.__raffle))
        application.add_handler(CommandHandler("raffle_list", self.__raffle_list))

    async def __raffle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

        await update.message.reply_text(reply_text)

    # A command for god to edit the list for the raffle
    async def __raffle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        self.entries = context.args
        print(self.entries)
