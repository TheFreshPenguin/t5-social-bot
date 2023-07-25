from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

from helpers.prompt_parser import parse

prompts = parse("resources/help_prompts.txt")


class HelpModule:
    def install(self, updater: Updater) -> None:
        updater.dispatcher.add_handler(CommandHandler("help", self.__help))

    def __help(self, update: Update, context: CallbackContext) -> None:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=prompts.get("welcome"),
            parse_mode="MarkdownV2",
        )
