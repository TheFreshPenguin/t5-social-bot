import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

from data.models.user import User
from data.repositories.user import UserRepository

from modules.base_module import BaseModule
from helpers.access_checker import AccessChecker
from helpers.exceptions import UserFriendlyError, CommandSyntaxError
from helpers.points import Points

from messages import donate_sarcasm

from integrations.loyverse.api import LoyverseApi
from integrations.loyverse.exceptions import InsufficientFundsError, InvalidCustomerError

logger = logging.getLogger(__name__)


class XmasModule(BaseModule):
    HELP_TEXT = "Express your appreciation for the staff this Christmas by donating some of your points. These will be distributed among our team on New Year's Eve!"
    SYNTAX_HELP_TEXT = "To use this command you need to write it like this:\n/xmas points\nFor example:\n/xmas 5"

    def __init__(self, loy: LoyverseApi, ac: AccessChecker, users: UserRepository, xmas_loyverse_id: str):
        self.loy: LoyverseApi = loy
        self.ac: AccessChecker = ac
        self.users: UserRepository = users
        self.recipient = User(full_name='Xmas Pot', loyverse_id=xmas_loyverse_id)

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("xmas", self._initiate),

            CommandHandler("start", self._help, filters.Regex('xmas')),

            CallbackQueryHandler(self._help, pattern="^xmas/help"),
            CallbackQueryHandler(self._confirm, pattern="^xmas/confirm/"),
            CallbackQueryHandler(self._cancel, pattern="^xmas/cancel"),
        ])
        logger.info("Xmas module installed")

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Donate to the Staff Xmas Pot', callback_data='xmas/help')],
        ]

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(f"{self.HELP_TEXT}\n\n{self.SYNTAX_HELP_TEXT}")

    async def _initiate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            point_string = XmasModule._parse_args(context.args)

            points = self._validate_points(point_string)
            sender = self._validate_sender(update)

            if update.message.chat.type == ChatType.PRIVATE:
                await update.message.reply_text(
                    f"You are about to donate {points} to the Staff Xmas Pot. Are you sure?",
                    reply_markup=XmasModule._confirm_keyboard(points)
                )
                return

            self._execute_donation(sender, points)

            messages = XmasModule._make_donation_messages(sender, points)

            await update.message.reply_text(messages['announcement'], quote=False)
        except CommandSyntaxError:
            await update.message.reply_text(self.SYNTAX_HELP_TEXT)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    @staticmethod
    def _parse_args(args: list[str]) -> str:
        if not args:
            raise CommandSyntaxError()

        # Proper form: /xmas 5 - this command can also have more text after the number
        if not args[0].isnumeric():
            raise CommandSyntaxError()

        return args[0]

    async def _confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            args = update.callback_query.data.split('/')
            if len(args) < 3:
                raise UserFriendlyError("There was an error and I could not understand your command. Please try again.")

            points = self._validate_points(args[2])
            sender = self._validate_sender(update)

            self._execute_donation(sender, points)

            messages = XmasModule._make_donation_messages(sender, points)

            await update.callback_query.answer()
            await update.callback_query.edit_message_text(messages['sender'])
        except UserFriendlyError as e:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    async def _cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("You were soooo close, but you turned away at the last moment. Don't worry - nobody else will know. It'll be our little secret.")

    def _validate_points(self, raw_points: str) -> Points:
        points = Points(raw_points)
        if not points.is_positive():
            raise UserFriendlyError("Your sense of charity is as high as the amount of points you tried to donate - donations have to be greater than zero.")

        return points

    def _validate_sender(self, update: Update) -> User:
        sender_name = update.effective_user.username
        if not sender_name:
            raise UserFriendlyError("I don't really know who you are - to use this feature you first need to create a username in Telegram.")

        sender = self.users.get_by_telegram_name(sender_name)
        if not sender:
            raise UserFriendlyError("Sorry, but this feature is for Community Champions only.")

        return sender

    def _execute_donation(self, sender: User, points: Points) -> None:
        if not self.ac.can_donate_for_free(sender):
            try:
                self.loy.remove_points(sender, points)
            except InvalidCustomerError as error:
                raise UserFriendlyError(f"You do not have a bar tab as a Community Champion. You should ask the hard-working elves at the bar to make one for you.") from error
            except InsufficientFundsError as error:
                raise UserFriendlyError("Your generosity is the stuff of legends, but you cannot donate more points than you have in your balance.") from error
            except Exception as error:
                raise UserFriendlyError("The donation has failed - perhaps the stars were not right? You can try again later.") from error

        try:
            self.loy.add_points(self.recipient, points)
        except InvalidCustomerError as error:
            raise UserFriendlyError(f"The donation has failed - it seems we can't find the Xmas Pot. We will get our elves to look for it and count every penny once again.") from error
        except Exception as error:
            raise UserFriendlyError("The donation has failed - perhaps the stars were not right? You can try again later.") from error

    @staticmethod
    def _make_donation_messages(sender: User, points: Points) -> dict[str, str]:
        sarc = donate_sarcasm.random

        return {
            "sender": f"{sarc} You donated {points} points to the Staff Xmas Pot.",
            "announcement": f"{sarc} {sender.friendly_name} donated {points} points to the Staff Xmas Pot.",
        }

    @staticmethod
    def _confirm_keyboard(points: Points) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                XmasModule._confirm_button(points, "Yes, I'm sure"),
                XmasModule._cancel_button("No, cancel"),
            ]
        ])

    @staticmethod
    def _confirm_button(points, text: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=f"xmas/confirm/{points}")

    @staticmethod
    def _cancel_button(text: str = 'Cancel') -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=f"xmas/cancel")
