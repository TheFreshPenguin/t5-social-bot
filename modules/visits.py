import logging
import pytz
from datetime import datetime, timedelta
from typing import Optional, Tuple

from telegram import Update, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import Application, ContextTypes, CommandHandler, CallbackQueryHandler

from data.models.user import User
from data.models.user_role import UserRole
from data.repositories.user import UserRepository

from modules.base_module import BaseModule
from helpers.points import Points
from helpers.visit_calculator import VisitCalculator, ReachedCheckpoints
from helpers.exceptions import UserFriendlyError

from integrations.loyverse.api import LoyverseApi
from integrations.loyverse.receipt import Receipt

from messages import visits_checkpoints

logger = logging.getLogger(__name__)


class VisitsModule(BaseModule):
    def __init__(self, loy: LoyverseApi, users: UserRepository, vc: VisitCalculator, timezone: pytz.timezone = None):
        self.loy = loy
        self.users = users
        self.timezone = timezone
        self.vc = vc

        # We start checking for visits from the first day of the current month
        self.last_check = datetime.now(self.timezone).replace(day=1, hour=0, minute=0, second=0)

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("visits", self._status),
            CallbackQueryHandler(self._status, pattern="^visits/status"),
        ])

        application.job_queue.run_once(callback=self._update_visits, when=0)
        application.job_queue.run_repeating(callback=self._update_visits, interval=60 * 5)

        logger.info(f"Visits module installed")

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Check Your Visits', callback_data='visits/status')],
        ]

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = self._validate_user(update)

            right_now = datetime.now(self.timezone)
            visits_this_month = VisitCalculator.get_visits_this_month(user, right_now)

            reply_parts = []
            if visits_this_month:
                reply_parts.append(f"You visited T5 {user.recent_visits} times this month!")
            else:
                reply_parts.append(f"I haven't seen you at T5 at all this month! Or maybe you're there right now for the first time?")

            if user.last_visit:
                if user.last_visit < right_now - timedelta(days=365):
                    date_format = '%d %B %Y'
                elif user.last_visit < right_now - timedelta(days=7):
                    date_format = '%d %B'
                else:
                    date_format = '%A, %d %B'
                reply_parts.append(f"The last time I saw you there was on {user.last_visit.strftime(date_format)}.")

            if VisitsModule._can_earn_points(user):
                next_checkpoint = self.vc.get_next_checkpoint(visits_this_month)
                if next_checkpoint:
                    visits_until_checkpoint = next_checkpoint[0] - visits_this_month
                    more = 'more ' if visits_this_month else ''
                    reply_parts.append(f"If you visit {visits_until_checkpoint} {more}times, you will be rewarded with {next_checkpoint[1]} points!")

            reply_parts.append(f"Please remember to pay your tab at the bar so I can tell you've been around.")

            reply = "\n\n".join(reply_parts)
        except UserFriendlyError as e:
            reply = str(e)
        except Exception as e:
            logger.exception(e)
            reply = f"BeeDeeBeeBoop 🤖 Error : {e}"

        if update.effective_chat.type != ChatType.PRIVATE:
            reply += "\n\n" + 'You can also <a href="https://t.me/T5socialBot?start=help">talk to me directly</a> to check your visits!'

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(reply, disable_web_page_preview=True)
        else:
            await update.message.reply_html(reply, disable_web_page_preview=True)

    async def _update_visits(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        # This function may take several seconds to run, so it's important that we sample the time at the start
        right_now = datetime.now(self.timezone)

        # Load fresh visits that came in since the last time we checked
        raw_visits = self._load_visits(self.last_check)
        updates = self.vc.add_visits(raw_visits, right_now)

        # Save the resulting user data to the repository
        self.users.save_all(list(updates.keys()))

        # Send messages to users about the points they received
        await self._send_messages(updates, right_now, context)

        # Remember when we last retrieved new information
        self.last_check = right_now

    def _load_visits(self, since: datetime) -> list[Tuple[User, datetime]]:
        # Load the receipts and convert them into visits (User + creation date)
        receipts = self.loy.get_receipts(since)
        raw_visits = [self._receipt_to_visit(receipt) for receipt in receipts]
        return [visit for visit in raw_visits if visit]

    def _receipt_to_visit(self, receipt: Receipt) -> Optional[Tuple[User, datetime]]:
        if not receipt.customer_id:
            return None

        user = self.users.get_by_loyverse_id(receipt.customer_id)
        if not user:
            return None

        return user, receipt.created_at

    async def _send_messages(self, updates: dict[User, ReachedCheckpoints], right_now: datetime, context: ContextTypes.DEFAULT_TYPE):
        updates_with_points = {user: points for user, points in updates.items() if points and VisitsModule._can_earn_points(user)}
        for user, month_checkpoints in updates_with_points.items():
            for month, checkpoints in month_checkpoints.items():
                total_points = sum(checkpoints.values(), start=Points(0))
                a_total_of = 'a total of ' if len(checkpoints) > 1 else ''
                self.loy.add_points(user, total_points)
                print(f"{user.full_name} receives {a_total_of}{total_points} point{total_points.plural} for visits in {month.strftime('%B')}")

                if user.telegram_id:
                    max_checkpoint = max(checkpoints.keys())
                    messages = visits_checkpoints.get(max_checkpoint, [])
                    message = (messages.random + "\n\n") if messages else None
                    month_text = 'this month' if month.month == right_now.month else f"in {month.strftime('%B')}"
                    announcement = f"{message}Because you visited us on {max_checkpoint} occasions {month_text}, we want to thank you for your persistence with {a_total_of}{total_points} point{total_points.plural}!"
                    await context.bot.send_message(user.telegram_id, announcement)

    def _validate_user(self, update: Update) -> User:
        sender_name = update.effective_user.username
        if not sender_name:
            raise UserFriendlyError("I don't really know who you are - you first need to create a username in Telegram.")

        sender = self.users.get_by_telegram_name(sender_name)
        if not sender:
            raise UserFriendlyError("Sorry, but this feature is for Community Champions only.")

        return sender

    @staticmethod
    def _can_earn_points(user: User) -> bool:
        return user.role != UserRole.STAFF
