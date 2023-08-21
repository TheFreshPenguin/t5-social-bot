from telegram import InlineKeyboardButton
from telegram.ext import Application


class BaseModule:
    def install(self, application: Application) -> None:
        pass

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return []
