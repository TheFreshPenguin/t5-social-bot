import logging
from collections import Counter

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from helpers.access_checker import AccessChecker
from helpers.exceptions import UserFriendlyError
from helpers.points import Points

from integrations.loyverse.api import LoyverseApi
from integrations.loyverse.exceptions import InsufficientFundsError

logger = logging.getLogger(__name__)


class RaffleModule:
    def __init__(self, loy: LoyverseApi, ac: AccessChecker):
        self.loy = loy
        self.ac = ac
        self.entries = []

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("raffle", self.__raffle))
        application.add_handler(CommandHandler("raffle_list", self.__raffle_list))
        logger.info(f"Raffle module installed")

    async def __raffle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.message.from_user.username

        try:
            if not user:
                raise UserFriendlyError('You first need to choose a username in Telegram')

            try:
                self.loy.remove_points(user, Points(5))
            except InsufficientFundsError as e:
                raise UserFriendlyError(f"Oh no @{user}! You don't have enough points for the Community Raffle. Buy some drinks from the bar or beg a friend for a donation!") from e

            self.entries.append(user)
            entry_count = Counter(self.entries)
            reply = f"Congrats @{user}. You just bought a ticket for the Community Raffle. Thanks for supporting and good luck!\n\n"

            # Display the list of entries with entry counts
            for entry, count in entry_count.items():
                reply += f"@{entry} - {count} Ticket(s)\n"

            await update.message.reply_text(reply)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    # A command for god to edit the list for the raffle
    async def __raffle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        self.entries = context.args
        logger.info(self.entries)
