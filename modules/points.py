import logging

from telegram import Update, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from data.models.user import User
from data.repositories.user import UserRepository

from modules.base_module import BaseModule
from helpers.exceptions import UserFriendlyError

from messages import points_balance_sarcasm

from integrations.loyverse.api import LoyverseApi

logger = logging.getLogger(__name__)


class PointsModule(BaseModule):
    def __init__(self, loy: LoyverseApi, users: UserRepository):
        self.loy = loy
        self.users = users

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("balance", self._balance),
            CallbackQueryHandler(self._balance, pattern="^points/balance$"),
        ])
        logger.info("Points module installed")

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Check Your Points', callback_data='points/balance')],
        ]

    async def _balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = self._validate_user(update)
            balance = self.loy.get_balance(user).to_integral()
            sarc = points_balance_sarcasm.random

            if update.effective_chat.type == ChatType.PRIVATE:
                reply = f"{sarc}\n\nYou have {balance} T5 Loyalty Points!"
            else:
                reply = (
                    f"{sarc} {user.main_alias or user.first_name}, you have {balance} T5 Loyalty Points!\n\n" +
                    'You can also <a href="https://t.me/T5socialBot?start=help">talk to me directly</a> to check your points!'
                )
        except UserFriendlyError as e:
            reply = str(e)
        except Exception as e:
            logger.exception(e)
            reply = f"BeeDeeBeeBoop 🤖 Error : {e}"

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(reply)
        else:
            await update.message.reply_html(reply)

    def _validate_user(self, update: Update) -> User:
        sender_name = update.effective_user.username
        if not sender_name:
            raise UserFriendlyError("I don't really know who you are - to donate or receive points you first need to create a username in Telegram.")

        sender = self.users.get_by_telegram_name(sender_name)
        if not sender:
            raise UserFriendlyError("Sorry, but this feature is for Community Champions only.")

        return sender
