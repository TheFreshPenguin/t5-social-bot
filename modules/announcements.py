import logging
import pytz
from datetime import time

from telegram.ext import Application, ContextTypes

from helpers.chat_target import ChatTarget

from modules.base_module import BaseModule

logger = logging.getLogger(__name__)


class AnnouncementsModule(BaseModule):
    def __init__(self, team_schedule_chats: set[ChatTarget], timezone: pytz.timezone = None):
        self.team_schedule_chats: set[ChatTarget] = team_schedule_chats.copy()
        self.timezone = timezone

    def install(self, application: Application) -> None:
        application.job_queue.run_daily(self._send_schedule_announcement, time(9, 0, 0, 0, self.timezone), days=(3,))

        logger.info("Announcements module installed")

    async def _send_schedule_announcement(self, context: ContextTypes.DEFAULT_TYPE):
        for target in self.team_schedule_chats:
            await context.bot.send_message(
                target.chat_id,
                'Don’t forget to send us your schedule requests and preferences before 5pm!',
                message_thread_id=target.thread_id,
            )
