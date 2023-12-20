import pytz
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from data.repositories.user import UserRepository

from modules.base_module import BaseModule

logger = logging.getLogger(__name__)


class TrackingModule(BaseModule):
    # This module must run on a separate group ID, so it runs even if a command in the main group has matched
    TRACKING_GROUP = 100

    def __init__(self, users: UserRepository, timezone: pytz.timezone = None):
        self.users = users
        self.timezone = timezone

    def install(self, application: Application) -> None:
        application.add_handlers([
            MessageHandler(filters.ChatType.PRIVATE, self.__track),
        ], group=self.TRACKING_GROUP)
        logger.info("Tracking module installed")

    async def __track(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user_name = update.effective_user.username
            if not user_name:
                return

            user = self.users.get_by_telegram_name(user_name)
            if not user:
                return

            user = user.copy(
                telegram_id=update.effective_user.id,
                last_private_chat=datetime.now(self.timezone)
            )
            self.users.save(user)
        except Exception as e:
            logger.exception(e)
