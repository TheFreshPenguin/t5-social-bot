import pytz
from datetime import datetime, time
from itertools import groupby
import csv
import random

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from helpers.loyverse import LoyverseConnector
from helpers.prompt_parser import parse

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
    def __init__(self, lc: LoyverseConnector, default_chats: set = None, points_to_award: int = 5, timezone: pytz.timezone = None):
        self.lc = lc
        self.chats = (default_chats or set()).copy()
        self.points_to_award = points_to_award
        self.timezone = timezone

    def install(self, updater: Updater) -> None:
        updater.dispatcher.add_handler(CommandHandler("start_announcing_birthdays", self.__start_announcing_birthdays))
        updater.dispatcher.add_handler(CommandHandler("stop_announcing_birthdays", self.__stop_announcing_birthdays))

        updater.job_queue.run_daily(self.__process_birthdays, time(0, 0, 0, 0, self.timezone))

    def __start_announcing_birthdays(self, update: Update, context: CallbackContext) -> None:
        self.chats.add(update.message.chat_id)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="I will announce birthdays in this chat, every day at midnight.",
        )

    def __stop_announcing_birthdays(self, update: Update, context: CallbackContext) -> None:
        self.chats.remove(update.message.chat_id)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="I will no longer announce birthdays in this chat.",
        )

    def __process_birthdays(self, context: CallbackContext) -> None:
        current_date = datetime.now()
        current_birthday = f"{current_date.month}/{current_date.day}"

        if current_birthday not in birthdays:
            return

        self.__add_points(birthdays[current_birthday])
        self.__announce_birthdays(birthdays[current_birthday], context)

    def __add_points(self, users: list[str]) -> None:
        for user in users:
            self.lc.add_points(user, self.points_to_award)

    def __announce_birthdays(self, users: list[str], context: CallbackContext) -> None:
        if not self.chats:
            return

        if not users:
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

        for chat_id in self.chats:
            context.bot.send_message(
                chat_id=chat_id,
                text=announcement,
            )
