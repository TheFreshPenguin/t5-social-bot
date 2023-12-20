import logging
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

from data.models.user import User
from data.repositories.user import UserRepository

from modules.base_module import BaseModule
from helpers.access_checker import AccessChecker
from helpers.exceptions import UserFriendlyError, CommandSyntaxError
from helpers.points import Points

from integrations.loyverse.api import LoyverseApi
from integrations.loyverse.exceptions import InsufficientFundsError, InvalidCustomerError

logger = logging.getLogger(__name__)

# sarcasm
with open("resources/donate_sarcasm.txt", "r") as file:
    sarcastic_comments = [line.rstrip('\n') for line in file.readlines()]


class DonateModule(BaseModule):
    HELP_TEXT = "To use this command you need to write it like this:\n/donate name points\nFor example:\n/donate Moni G 5"

    def __init__(self, loy: LoyverseApi, ac: AccessChecker, users: UserRepository, announcement_chats: set[int] = None):
        self.loy: LoyverseApi = loy
        self.ac: AccessChecker = ac
        self.users: UserRepository = users
        self.announcement_chats: set[int] = (announcement_chats or set()).copy()

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("donate", self._initiate),

            CommandHandler("start", self._initiate, filters.Regex('donate')),

            CallbackQueryHandler(self._help, pattern="^donate/help"),
            CallbackQueryHandler(self._confirm, pattern="^donate/confirm/"),
            CallbackQueryHandler(self._cancel, pattern="^donate/cancel"),
        ])
        logger.info("Donate module installed")

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Donate Points', callback_data='donate/help')],
        ]

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(self.HELP_TEXT)

    async def _initiate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            recipient_name, point_string = DonateModule._parse_args(context.args)

            points = self._validate_points(point_string)
            sender = self._validate_sender(update)
            recipients = self._validate_possible_recipients(recipient_name, sender)

            recipient = list(recipients)[0] if len(recipients) == 1 else None

            if update.message.chat.type == ChatType.PRIVATE:
                if recipient:
                    await update.message.reply_text(
                        f"You are about to donate {points} to {DonateModule._search_name(recipient)}. Are you sure?",
                        reply_markup=DonateModule._confirm_keyboard(recipient, points)
                    )
                else:
                    await update.message.reply_text(
                        "There is more than one person who goes by that name. Please select the right one from the choices below.",
                        reply_markup=DonateModule._choose_keyboard(recipients, points)
                    )
                return

            if not recipient:
                # This passthrough is parsed by the private chat, so you can continue donating to the same user
                passthrough = f"donate_{recipient_name.replace(' ', '-')}_{points}"
                await update.message.reply_html(f"There is more than one person who goes by that name. Please <a href=\"https://t.me/T5socialBot?start={passthrough}\">contact me in private</a> so I can help you find the right one.")
                return

            self._execute_donation(sender, recipient, points)

            messages = DonateModule._make_donation_messages(sender, recipient, points)

            await update.message.reply_text(messages['announcement'], quote=False)
            if recipient.telegram_id:
                await context.bot.send_message(recipient.telegram_id, messages['recipient'])
        except CommandSyntaxError:
            await update.message.reply_text(self.HELP_TEXT)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    @staticmethod
    def _parse_args(args: list[str]) -> tuple[str, str]:
        if not args:
            raise CommandSyntaxError()

        if len(args) == 1:
            return DonateModule._parse_single_argument_form(args)

        return DonateModule._parse_multi_argument_form(args)

    @staticmethod
    def _parse_single_argument_form(args: list[str]) -> tuple[str, str]:
        # One argument: /start donate_Moni-G_5
        # This form is only used when switching from group chat to private chat
        tokens = args[0].split('_')
        if tokens[0] != 'donate' or len(tokens) < 3:
            raise CommandSyntaxError()

        recipient_name = "_".join(tokens[1: -1]).replace('-', ' ')
        point_string = tokens[-1]

        return recipient_name, point_string

    @staticmethod
    def _parse_multi_argument_form(args: list[str]) -> tuple[str, str]:
        # 2 or more arguments: /donate Moni G 5 - this command can also have more text after the number
        # The name may have spaces in it, which the library interprets as separate arguments
        # Parsing the name stops when we come across a number and ignore any text after it
        i = 0
        while (i < len(args)) and (not args[i].isnumeric()):
            i += 1

        if i >= len(args):
            raise CommandSyntaxError()

        recipient_name = " ".join(args[0:i]).lstrip('@')
        point_string = args[i]

        return recipient_name, point_string

    async def _confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            args = update.callback_query.data.split('/')
            if len(args) < 4:
                raise UserFriendlyError("There was an error and I could not understand your command. Please try again.")

            points = self._validate_points(args[3])
            sender = self._validate_sender(update)
            recipient = self._validate_recipient_direct(args[2], sender)

            self._execute_donation(sender, recipient, points)

            messages = DonateModule._make_donation_messages(sender, recipient, points)

            await update.callback_query.answer()
            await update.callback_query.edit_message_text(messages['sender'])

            if recipient.telegram_id:
                await context.bot.send_message(recipient.telegram_id, messages['recipient'])
            else:
                for chat_id in self.announcement_chats:
                    await context.bot.send_message(chat_id, messages['announcement'])
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
            raise UserFriendlyError("I don't really know who you are - to donate or receive points you first need to create a username in Telegram.")

        sender = self.users.get_by_telegram_name(sender_name)
        if not sender:
            raise UserFriendlyError("Sorry, but the donate feature is for Community Champions only.")

        return sender

    def _validate_possible_recipients(self, query: str, sender: User) -> set[User]:
        if len(query) < 3:
            raise UserFriendlyError("Minimalism is a quality to be admired, but not when looking for people's names. Please try a longer name.")

        recipients = self.users.search(query)
        if not recipients:
            raise UserFriendlyError("I don't know this strange person that you are trying to donate to - is this one of our Community Champions?")

        # Don't allow sending to yourself
        recipients.discard(sender)
        # If the set is empty after removing the sender, then we were trying to donate to ourselves
        if not recipients:
            raise UserFriendlyError("Donating to yourself is like high-fiving in a mirror – impressive to you, but not making the world a better place!")

        return recipients

    def _validate_recipient_direct(self, telegram_name: str, sender: User) -> User:
        recipient = self.users.get_by_telegram_name(telegram_name)
        if not recipient:
            raise UserFriendlyError("I don't know this strange person that you are trying to donate to - is this one of our Community Champions?")

        if sender == recipient:
            raise UserFriendlyError("Donating to yourself is like high-fiving in a mirror – impressive to you, but not making the world a better place!")

        return recipient

    def _execute_donation(self, sender: User, recipient: User, points: Points) -> None:
        if not self.ac.can_donate_for_free(sender):
            try:
                self.loy.remove_points(sender, points)
            except InvalidCustomerError as error:
                raise UserFriendlyError(f"You do not have a bar tab as a Community Champion. You should ask Rob to make one for you.") from error
            except InsufficientFundsError as error:
                raise UserFriendlyError("Your generosity is the stuff of legends, but you cannot donate more points than you have in your balance.") from error
            except Exception as error:
                raise UserFriendlyError("The donation has failed - perhaps the stars were not right? You can try again later.") from error

        try:
            self.loy.add_points(recipient, points)
        except InvalidCustomerError as error:
            raise UserFriendlyError(f"{DonateModule._message_name(recipient)} does not have a bar tab as a Community Champion. You should ask Rob to make one for them.") from error
        except Exception as error:
            raise UserFriendlyError("The donation has failed - perhaps the stars were not right? You can try again later.") from error

    @staticmethod
    def _make_donation_messages(sender: User, recipient: User, points: Points) -> dict[str, str]:
        sarc = random.choice(sarcastic_comments).rstrip('\n')

        return {
            "sender": f"{sarc} You donated {points} points to {DonateModule._message_name(recipient)}.",
            "recipient": f"{DonateModule._message_name(sender)} donated {points} to you!",
            "announcement": f"{sarc} {DonateModule._message_name(sender)} donated {points} points to {DonateModule._message_name(recipient)}.",
        }

    @staticmethod
    def _confirm_keyboard(recipient: User, points: Points) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                DonateModule._confirm_button(recipient, points, "Yes, I'm sure"),
                DonateModule._cancel_button("No, cancel"),
            ]
        ])

    @staticmethod
    def _choose_keyboard(recipients: set[User], points: Points) -> InlineKeyboardMarkup:
        recipients = sorted(recipients, key=lambda u: u.aliases[0] if u.aliases else u.full_name)
        buttons = [DonateModule._confirm_button(u, points) for u in recipients]
        buttons.append(DonateModule._cancel_button())

        return InlineKeyboardMarkup([[b] for b in buttons])

    @staticmethod
    def _confirm_button(user: User, points, text: str = '') -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text or DonateModule._search_name(user),
            callback_data=f"donate/confirm/{user.telegram_username}/{points}"
        )

    @staticmethod
    def _cancel_button(text: str = 'Cancel') -> InlineKeyboardButton:
        return InlineKeyboardButton(text, callback_data=f"donate/cancel")

    @staticmethod
    def _message_name(user: User) -> str:
        name = user.main_alias or user.first_name
        return f"{name} / @{user.telegram_username}"

    @staticmethod
    def _search_name(user: User) -> str:
        name = user.main_alias or user.full_name
        return f"{name} / @{user.telegram_username}"
