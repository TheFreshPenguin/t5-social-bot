from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from helpers.prompt_parser import parse

prompts = parse("resources/help_prompts.txt")


class HelpModule:
    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("help", self.__help))

    async def __help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_markdown_v2(prompts.get("welcome"))
