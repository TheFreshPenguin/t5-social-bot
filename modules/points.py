import logging
import random

from telegram import Update, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from modules.base_module import BaseModule
from helpers.access_checker import AccessChecker
from helpers.exceptions import UserFriendlyError
from helpers.points import Points

from integrations.loyverse.api import LoyverseApi
from integrations.loyverse.exceptions import InsufficientFundsError

logger = logging.getLogger(__name__)

# sarcasm
with open("resources/points_donate_sarcasm.txt", "r") as file:
    donate_sarcastic_comments = [line.rstrip('\n') for line in file.readlines()]

with open("resources/points_balance_sarcasm.txt", "r") as file:
    balance_sarcastic_comments = [line.rstrip('\n') for line in file.readlines()]


class PointsModule(BaseModule):
    def __init__(self, loy: LoyverseApi, ac: AccessChecker):
        self.loy = loy
        self.ac = ac

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("balance", self.__balance),
            CommandHandler("donate", self.__donate),

            CallbackQueryHandler(self.__balance, pattern="^points/balance$"),
            CallbackQueryHandler(self.__donate_help, pattern="^points/donate_help"),
        ])
        logger.info("Points module installed")

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Check Your Points', callback_data='points/balance')],
            [InlineKeyboardButton('Donate Points', callback_data='points/donate_help')],
        ]

    async def __balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = update.effective_user.username
            if not user:
                raise UserFriendlyError("I don't really know who you are - to check your balance you first need to create a username in Telegram.")

            balance = self.loy.get_balance(user).to_integral()
            sarc = random.choice(balance_sarcastic_comments)
            reply = f"{sarc} @{user}, you have {balance} T5 Loyalty Points!"
        except UserFriendlyError as e:
            reply = str(e)
        except Exception as e:
            logger.exception(e)
            reply = f"BeeDeeBeeBoop 🤖 Error : {e}"

        if update.effective_chat.type != ChatType.PRIVATE:
            reply += "\n\n" + 'You can also <a href="https://t.me/T5socialBot?start=help">talk to me directly</a> to check your points!'

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(reply)
        else:
            await update.message.reply_html(reply)

    async def __donate_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "To use this command you need to write it like this: /donate telegram_username number_of_points"
        )

    async def __donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Get the arguments passed with the command
        args = context.args

        try:
            if len(args) < 2:
                raise UserFriendlyError("To use this command you need to write it like this: /donate telegram_username number_of_points")

            sender = update.effective_user.username
            if not sender:
                raise UserFriendlyError("I don't really know who you are - to donate or receive points you first need to create a username in Telegram.")

            recipient = args[0].lstrip('@')
            if sender == recipient:
                raise UserFriendlyError("Donating to yourself is like high-fiving in a mirror – impressive to you, but not making the world a better place!")

            points = Points(args[1])
            if not points.is_positive():
                raise UserFriendlyError("Your sense of charity is as high as the amount of points you tried to donate - donations have to be greater than zero.")

            try:
                if not self.ac.can_donate_for_free(sender):
                    self.loy.remove_points(sender, points)

                self.loy.add_points(recipient, points)
            except InsufficientFundsError as error:
                raise UserFriendlyError("Your generosity is the stuff of legends, but you cannot donate more points than you have in your balance.") from error
            except Exception as error:
                raise UserFriendlyError("The donation has failed - perhaps the stars were not right? You can try again later.") from error

            sarc = random.choice(donate_sarcastic_comments).rstrip('\n')
            if update.message.chat.type == ChatType.PRIVATE:
                reply = f"{sarc} You donated {args[1]} points to {args[0]}."
            else:
                reply = f"{sarc} @{sender} donated {args[1]} points to {args[0]}."

            await update.message.reply_text(reply)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")
