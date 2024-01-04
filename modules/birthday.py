import logging
import pytz
from typing import Optional
from datetime import datetime, time
import random

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

from data.models.user import User
from data.repositories.user import UserRepository

from modules.base_module import BaseModule
from helpers.access_checker import AccessChecker
from helpers.points import Points
from helpers.prompt_parser import parse

from integrations.loyverse.api import LoyverseApi

logger = logging.getLogger(__name__)

prompts = parse("resources/birthday_prompts.txt")

with open("resources/birthday_messages.txt", "r") as file:
    birthday_messages = [line.rstrip('\n') for line in file.readlines()]


class BirthdayModule(BaseModule):
    def __init__(self, loy: LoyverseApi, ac: AccessChecker, users: UserRepository, announcement_chats: set[int] = None, points_to_award: Points = Points(5), timezone: Optional[pytz.timezone] = None):
        self.loy: LoyverseApi = loy
        self.ac: AccessChecker = ac
        self.users: UserRepository = users
        self.announcement_chats: set[int] = (announcement_chats or set()).copy()
        self.points_to_award: Points = points_to_award
        self.timezone: Optional[pytz.timezone] = timezone

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler('force_announce_birthdays', self._force_announce_birthdays, filters.ChatType.PRIVATE))

        daily_time = time(0, 0, 0, 0, self.timezone)
        application.job_queue.run_daily(self._process_birthdays, daily_time)

        logger.info("Birthday module installed")

    async def _force_announce_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        await self._process_birthdays(context)

    async def _process_birthdays(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        current_date = datetime.now(self.timezone)
        logger.info(f"Processing birthdays for {current_date}.")

        users = self.users.get_by_birthday(current_date)
        if not users:
            logger.info("No users have birthdays today")
            return

        logger.info(f"The following users have birthdays today: {users}")

        self._add_points(users)
        await self._announce_birthdays(users, context)

    def _add_points(self, users: list[User]) -> None:
        for user in users:
            self.loy.add_points(user, self.points_to_award)

    async def _announce_birthdays(self, users: list[User], context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.announcement_chats:
            logger.warning('There are no chats to announce the birthdays to.')
            return

        if not users:
            return

        users_text = BirthdayModule._enumerate([BirthdayModule._message_name(user) for user in users])

        announcement = prompts.get('birthday_announcement').format(
            users=users_text,
            message=random.choice(birthday_messages),
            points=self.points_to_award
        )

        for chat_id in self.announcement_chats:
            await context.bot.send_message(chat_id, announcement)

    @staticmethod
    def _message_name(user: User) -> str:
        name = user.main_alias or user.first_name
        return f"{name} / @{user.telegram_username}"

    @staticmethod
    def _enumerate(lst: list[str]) -> str:
        return (', '.join(lst[:-1]) + ' and ' + lst[-1]) if len(lst) > 1 else lst[0]
