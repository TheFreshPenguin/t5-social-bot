import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from modules.base_module import BaseModule

logger = logging.getLogger(__name__)

WELCOME_PUBLIC = """BeeDeeBeeBoop 🤖

I am the T5 Social Telegram bot!

<a href="https://t.me/T5socialBot?start=help">Talk to me directly</a> to learn how I can be of help!
"""

WELCOME_PRIVATE = """I am the T5 Social Telegram bot!

Did you know that every time you visit T5, 5% of your spend is converted into <b>Loyalty Points</b>? These can be redeemed on future visits, or even gifted to others!

You can use me to check your points balance or donate points to a friend.

I can also inform you about upcoming <b>Social Events</b> in the community.

How can I assist you today?

Made with ❤️ by <a href="tg://user?id=1698340339">Antoine</a>
"""


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
            await update.message.reply_html(WELCOME_PRIVATE, reply_markup=self.__menu_keyboard(), disable_web_page_preview=True)
            return

        await update.message.reply_html(WELCOME_PUBLIC, disable_web_page_preview=True)

    def __menu_keyboard(self) -> InlineKeyboardMarkup:
        menu = [module.get_menu_buttons() for module in self.menu_modules]
        flat_menu = [item for sublist in menu for item in sublist]

        return InlineKeyboardMarkup(flat_menu)
