import pytz
from datetime import datetime, time, timedelta
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

from modules.base_module import BaseModule
from helpers.access_checker import AccessChecker
from helpers.exceptions import UserFriendlyError
from helpers.chat_target import ChatTarget
from data.repositories.event import EventRepository
from data.models.event import Event

logger = logging.getLogger(__name__)


class EventsModule(BaseModule):
    def __init__(self, ac: AccessChecker, repository: EventRepository, timezone: pytz.timezone = None, upcoming_days: int = 6, admin_chats: set[ChatTarget] = None):
        self.ac = ac
        self.repository = repository
        self.timezone = timezone
        self.upcoming_days = upcoming_days
        self.admin_chats: set[ChatTarget] = (admin_chats or set()).copy()

    def install(self, application: Application) -> None:
        application.add_handlers([
            CommandHandler('start', self._display_events, filters.Regex('event')),
            CommandHandler('event', self._display_events),
            CommandHandler('events', self._display_events),
            CallbackQueryHandler(self._display_events, pattern='^events/list$'),
        ])

        daily_time = time(0, 0, 0, 0, self.timezone)
        application.job_queue.run_daily(self._announce_advance_events, daily_time, days=(0,))

        logger.info('Events module installed')

    def get_menu_buttons(self) -> list[list[InlineKeyboardButton]]:
        return [
            [InlineKeyboardButton('Upcoming Social Events', callback_data='events/list')],
        ]

    async def _display_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # This command can only be run in private chats, except if you are a bot master
        if not (update.callback_query or update.message.chat.type == ChatType.PRIVATE) and not self.ac.is_master(update.effective_user.username):
            return

        try:
            now = datetime.now(self.timezone)
            today_text = self._format_today(now)
            upcoming_text = self._format_upcoming(now, self.upcoming_days)
            reply = self._merge_texts(today_text, upcoming_text)
        except UserFriendlyError as e:
            reply = str(e)
        except Exception as e:
            logger.exception(e)
            reply = f"BeeDeeBeeBoop 🤖 Error : {e}"

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(reply, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_html(reply)

    @staticmethod
    def _merge_texts(today: str, upcoming: str) -> str:
        if today and upcoming:
            return f"{today}\n\n<b>Upcoming Events:</b>\n\n{upcoming}"
        elif today:
            return today
        elif upcoming:
            return f"There are no events today, but here are some <b>Upcoming Events</b>:\n\n{upcoming}"
        else:
            return "Sadly, Mici has eaten all our hosts so there are no events happening any time soon."

    async def _announce_advance_events(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.admin_chats:
            return

        upcoming_text = self._format_upcoming(datetime.now(self.timezone), self.upcoming_days + 1)

        if upcoming_text:
            announcement = f"<b>Upcoming Events:</b>\n\n{upcoming_text}\n\nDoes this look right?"
        else:
            announcement = f"⚠️ There are no upcoming events in the next {self.upcoming_days + 1} days. Remember to add some in the Google sheet! ⚠️"

        for target in self.admin_chats:
            await context.bot.send_message(target.chat_id, announcement, parse_mode=ParseMode.HTML, message_thread_id=target.thread_id)

    def _format_today(self, now: datetime) -> str:
        events = self.repository.get_events_on(now)
        events = [e for e in events if e.end_date > now]

        if not events:
            return ""

        main_event = events[-1]
        main_text = EventsModule._main_event(main_event, now)
        today_text = f"<b>Tonight's Event:</b>\n\n{main_text}"

        if len(events) > 1:
            secondary_events = events[0:-1]
            secondary_text = "\n".join([EventsModule._upcoming_event(e, now) for e in secondary_events])
            today_text += f"\n\n<b>Also Happening:</b>\n\n{secondary_text}"

        return today_text

    def _format_upcoming(self, now: datetime, upcoming_days: int) -> str:
        upcoming_texts = []
        for date in (now + timedelta(n + 1) for n in range(upcoming_days)):
            date_events = self.repository.get_events_on(date)
            if not date_events:
                continue

            date_heading = date.strftime('%A, %d %B').replace(' 0', ' ')
            date_texts = [EventsModule._upcoming_event(e) for e in date_events]

            upcoming_texts.append(date_heading + "\n" + "\n".join(date_texts))

        return "\n\n".join(upcoming_texts)

    @staticmethod
    def _main_event(e: Event, now: datetime) -> str:
        return (
            f"{e.name} @ {EventsModule._event_time(e.start_date, now)}"
            + (f"\nHosted by {e.host}" if e.host else "")
            + (f"\n{e.description}" if e.description else "")
        )

    @staticmethod
    def _upcoming_event(e: Event, now: Optional[datetime] = None) -> str:
        return f"{e.name} | {EventsModule._event_time(e.start_date, now)}" + (f" | {e.host}" if e.host else "")

    @staticmethod
    def _event_time(date: datetime, now: Optional[datetime] = None) -> str:
        return "<b>RIGHT NOW</b>" if (now and date < now) else date.strftime('%I:%M%p').lstrip('0').replace(':00', '').lower()

    @staticmethod
    def _enumerate(lst: list[str]) -> str:
        return (', '.join(lst[:-1]) + ' and ' + lst[-1]) if len(lst) > 1 else lst[0]
