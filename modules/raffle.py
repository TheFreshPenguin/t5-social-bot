import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

from data.repositories.user import UserRepository
from data.models.raffle_entry import RaffleEntry
from data.models.user import User

from helpers.exceptions import UserFriendlyError
from helpers.raffle import Raffle
from modules.base_module import BaseModule

from integrations.loyverse.exceptions import InsufficientFundsError

logger = logging.getLogger(__name__)

HELP_PUBLIC = """Entry: 5 Loyalty Points
Deadline: 23rd June
Maximum 3 entries

When you type /euro we give you a random nation to support during the European Championships!
If your country is the best performing, you take all the Loyalty Points! Please note it’s possible for multiple people to share a nation.

You can also <a href="https://t.me/T5socialBot?start=raffle">talk to me directly</a> to participate!
"""

HELP_PRIVATE = """Entry: 5 Loyalty Points
Deadline: 23rd June
Maximum 3 entries

When you enter the sweepstakes we give you a random nation to support during the European Championships!
If your country is the best performing, you take all the Loyalty Points! Please note it’s possible for multiple people to share a nation."""


class RaffleModule(BaseModule):
    def __init__(self, raffle: Raffle, users: UserRepository):
        self.raffle = raffle
        self.users = users

    def install(self, application: Application) -> None:
        if not self.raffle.is_active:
            return

        application.add_handlers([
            CommandHandler("start", self._help, filters.Regex('raffle')),
            CommandHandler("euro", self._initiate),

            CallbackQueryHandler(self._button_clicked)
        ])
        logger.info(f"Raffle module installed")

    async def _button_clicked(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query

        if query.data == "raffle/help":
            await self._help(update, context)
        elif query.data == "raffle/buy":
            await self._buy(update, context)
        elif query.data == "raffle/list_entries":
            await self._list_entries(update, context)

    async def _initiate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat.type == ChatType.PRIVATE:
            await self._help(update, context)
            return

        try:
            user = self._validate_user(update)

            result = self._execute_buy(user)

            await update.message.reply_html(result + "\n\n" + HELP_PUBLIC, disable_web_page_preview=True)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = self._validate_user(update)
            keyboard = self._menu_keyboard('raffle/help', user)

            entries = self.raffle.get_entries(user)
            if not entries:
                country_message = ""
            elif len(entries) > 1:
                country_message = f"\n\nYour countries are: {self.format_entries(entries)}"
            else:
                country_message = f"\n\nYour country is {self.format_entries(entries)}."

            message = HELP_PRIVATE + country_message

            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(message, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_html(message, reply_markup=keyboard, disable_web_page_preview=True)
        except UserFriendlyError as e:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(str(e))
            else:
                await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(f"BeeDeeBeeBoop 🤖 Error : {e}")
            else:
                await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")
                await update.message.reply_text(str(e))

    async def _buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = self._validate_user(update)

            message = self._execute_buy(user)

            keyboard = self._menu_keyboard('raffle/bought', user)

            await update.callback_query.answer(f"You have joined the {self.raffle.title}!")
            await update.callback_query.edit_message_text(message, reply_markup=keyboard)
        except UserFriendlyError as e:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    def _execute_buy(self, user: User) -> str:
        if not self.raffle.can_enter(user):
            raise UserFriendlyError(f"You already have {self.raffle.max_tickets} entries so any more than this will get you a red card!")

        try:
            self.raffle.buy_ticket(user)
        except InsufficientFundsError as error:
            raise UserFriendlyError(f"Oh no! You don't have enough points for the {self.raffle.title}. Buy some drinks from the bar or beg a friend for a donation!") from error

        entries = self.raffle.get_entries(user)
        if not entries:
            country_message = ""
        elif len(entries) > 1:
            country_message = f"\n\nYour countries are: {self.format_entries(entries)}"
        else:
            country_message = f"\n\nYour country is {self.format_entries(entries)}."

        return f"Congrats {user.main_alias or user.first_name}! You just bought a ticket for the {self.raffle.title}!{country_message}\n\nThanks for supporting and good luck!"

    async def _list_entries(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = self._validate_user(update)

            if self.raffle.entries:
                text = f"The following people are playing in the {self.raffle.title}:\n\n"

                for full_name, entries in self.raffle.entries.list_by_user().items():
                    user = self.users.get_by_full_name(full_name)
                    if not user:
                        continue
                    text += f"{user.friendly_name} - {self.format_entries(entries)}\n"
            else:
                text = "Nobody is playing yet! Will you be the one to break the ice?"

            keyboard = self._menu_keyboard('raffle/list_entries', user)

            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text, reply_markup=keyboard)
            else:
                await update.message.reply_text(text, reply_markup=keyboard)
        except UserFriendlyError as e:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    def _menu_keyboard(self, current_entry: str, user: User) -> InlineKeyboardMarkup:
        if self.raffle.can_enter(user):
            if self.raffle.has_entries(user):
                buy = InlineKeyboardButton("One more ticket, please!", callback_data="raffle/buy")
            else:
                buy = InlineKeyboardButton("I want to join!", callback_data="raffle/buy")
        else:
            buy = None

        buttons = [
            buy,
            InlineKeyboardButton("Who's playing?", callback_data="raffle/list_entries"),
            InlineKeyboardButton("How does it work?", callback_data="raffle/help"),
        ]

        buttons = [button for button in buttons if button and button.callback_data != current_entry]

        if len(buttons) == 3:
            buttons = [
                [buttons[0]],
                [buttons[1], buttons[2]]
            ]
        else:
            buttons = [buttons]

        return InlineKeyboardMarkup(buttons)

    def format_entries(self, entries: list[RaffleEntry]) -> str:
        return self._enumerate([entry.country for entry in entries])

    @staticmethod
    def _enumerate(lst: list[str]) -> str:
        return (', '.join(lst[:-1]) + ' and ' + lst[-1]) if len(lst) > 1 else lst[0]

    def _validate_user(self, update: Update) -> User:
        sender_name = update.effective_user.username
        if not sender_name:
            raise UserFriendlyError("I don't really know who you are - to donate or receive points you first need to create a username in Telegram.")

        sender = self.users.get_by_telegram_name(sender_name)
        if not sender:
            raise UserFriendlyError("Sorry, but this feature is for Community Champions only.")

        return sender
