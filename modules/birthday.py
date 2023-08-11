import logging
import pytz
from datetime import datetime, time
from itertools import groupby
import csv
import random

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from helpers.access_checker import AccessChecker
from helpers.points import Points
from helpers.prompt_parser import parse

from integrations.loyverse.api import LoyverseApi

logger = logging.getLogger(__name__)

prompts = parse("resources/birthday_prompts.txt")

with open("resources/birthday_messages.txt", "r") as file:
    birthday_messages = [line.rstrip('\n') for line in file.readlines()]


# The keys are birthdays, the values are lists of users without @
birthdays = {}

# Open the CSV file
with open('resources/T5 Community Data_Birthdays.csv', 'r') as csvfile:
    # Create a CSV reader object
    reader = csv.DictReader(csvfile)

    birthday_data = [(f"{row['Month']}/{row['Day']}", row['Username']) for row in reader]
    sorted_birthdays = sorted(birthday_data, key=lambda row: row[0])
    for date, grouped_users in groupby(sorted_birthdays, key=lambda row: row[0]):
        birthdays[date] = [user[1] for user in grouped_users]


class BirthdayModule:
    def __init__(self, loy: LoyverseApi, ac: AccessChecker, default_chats: set = None, points_to_award: Points = Points(5), timezone: pytz.timezone = None):
        self.loy = loy
        self.ac = ac
        self.chats = (default_chats or set()).copy()
        self.points_to_award = points_to_award
        self.timezone = timezone

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("start_announcing_birthdays", self.__start_announcing_birthdays))
        application.add_handler(CommandHandler("stop_announcing_birthdays", self.__stop_announcing_birthdays))
        application.add_handler(CommandHandler("force_announce_birthdays", self.__force_announce_birthdays))

        daily_time = time(0, 0, 0, 0, self.timezone)
        application.job_queue.run_daily(self.__process_birthdays, daily_time)

        logger.info(f"Birthday module installed with config: chats: {self.chats} / points_to_award: {self.points_to_award} / timezone: {self.timezone} / daily_time: {daily_time}")

    async def __start_announcing_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        self.chats.add(update.effective_chat.id)
        await update.message.reply_text("I will announce birthdays in this chat, every day at midnight.")
        logger.info(f'Birthdays will be announced to {self.chats}')

    async def __stop_announcing_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        self.chats.remove(update.effective_chat.id)
        await update.message.reply_text("I will no longer announce birthdays in this chat.")
        logger.info(f'Birthdays will be announced to {self.chats}')

    async def __force_announce_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.ac.is_master(update.effective_user.username):
            return

        await self.__process_birthdays(context)

    async def __process_birthdays(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        current_date = datetime.now(self.timezone)
        current_birthday = f"{current_date.month}/{current_date.day}"
        logger.info(f"It is now {current_date} . Processing birthdays for {current_birthday} .")

        users = birthdays.get(current_birthday, [])
        if not users:
            logger.info("No users have birthdays today")
            return

        logger.info(f"The following users have birthdays today: {users}")

        self.__add_points(users)
        await self.__announce_birthdays(users, context)

    def __add_points(self, users: list[str]) -> None:
        for user in users:
            self.loy.add_points(user, self.points_to_award)

    async def __announce_birthdays(self, users: list[str], context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.chats:
            logger.warning('There are no chats to announce the birthdays to.')
            return

        if not users:
            logger.warning('There are no users to include in the birthday announcement.')
            return

        usernames = [f"@{user}" for user in users]

        if len(usernames) == 1:
            users_text = usernames[0]
        else:
            users_text = ', '.join(usernames[0:-1]) + ' and ' + usernames[-1]

        announcement = prompts.get('birthday_announcement').format(
            users=users_text,
            message=random.choice(birthday_messages),
            points=self.points_to_award
        )

        logger.info(announcement)

        for chat_id in self.chats:
            await context.bot.send_message(chat_id, announcement)
