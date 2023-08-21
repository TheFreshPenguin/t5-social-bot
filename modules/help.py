import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from modules.base_module import BaseModule
from helpers.prompt_parser import parse

logger = logging.getLogger(__name__)

prompts = parse("resources/help_prompts.txt")


class HelpModule(BaseModule):
    def __init__(self, menu_modules: list[BaseModule]):
        self.menu_modules = menu_modules

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler("start", self.__help, filters.Regex('help') & filters.ChatType.PRIVATE),
            CommandHandler("help", self.__help),
            MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, self.__help),
        ])

        logger.info("Help module installed")

    async def __help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat.type == ChatType.PRIVATE:
            await update.message.reply_markdown_v2(prompts.get("welcome"), reply_markup=self.__menu_keyboard())
            return

        await update.message.reply_markdown_v2(prompts.get("welcome_general"))

    def __menu_keyboard(self) -> InlineKeyboardMarkup:
        menu = [module.get_menu_buttons() for module in self.menu_modules]
        flat_menu = [item for sublist in menu for item in sublist]

        return InlineKeyboardMarkup(flat_menu)
