import pytz
from datetime import datetime, timedelta
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

from helpers.exceptions import UserFriendlyError
from data.repository import DataRepository
from data.models.event import Event

logger = logging.getLogger(__name__)


class EventsModule:
    def __init__(self, repository: DataRepository, timezone: pytz.timezone = None, upcoming_days: int = 6):
        self.repository = repository
        self.timezone = timezone
        self.upcoming_days = upcoming_days

    def install(self, application: Application) -> None:
        application.add_handler(CommandHandler("start", self.__display_events, filters.Regex('event')))
        application.add_handler(CommandHandler("event", self.__display_events))
        application.add_handler(CommandHandler("events", self.__display_events))
        logger.info("Events module installed")

    async def __display_events(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            all_events = self.repository.get_events()
            now = datetime.now(self.timezone)

            today_text = self.__format_today(all_events, now)
            upcoming_text = self.__format_upcoming(all_events, now, self.upcoming_days)
            reply = self.__merge_texts(today_text, upcoming_text)

            await update.message.reply_html(reply)
        except UserFriendlyError as e:
            await update.message.reply_text(str(e))
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(f"BeeDeeBeeBoop 🤖 Error : {e}")

    @staticmethod
    def __merge_texts(today: str, upcoming: str) -> str:
        if today and upcoming:
            return today + "\n\n" + "Here are other <b>Upcoming Events</b>:\n\n" + upcoming
        elif today:
            return today
        elif upcoming:
            return "There are no events today, but here are some <b>Upcoming Events</b>:\n\n" + upcoming
        else:
            return "Sadly, Mici has eaten all our hosts so there are no events happening any time soon."

    @staticmethod
    def __format_today(all_events: dict[str, list[Event]], now: datetime) -> str:
        events = all_events.get(now.strftime('%Y-%m-%d'), [])
        events = [e for e in events if e.end_date > now]

        if not events:
            return ""

        main_event = events[-1]
        main_text = EventsModule.__today_event(events[-1], now)
        today_text = f"Join us today for {main_text}!"

        if main_event.description:
            today_text += f"\n{main_event.description}"

        if len(events) > 1:
            secondary_events = events[0:-1]
            secondary_text = EventsModule.__enumerate([EventsModule.__today_event(e, now) for e in secondary_events])
            today_text += f"\n\nBut wait, there's more!\nWe also have {secondary_text}."

        return today_text

    @staticmethod
    def __format_upcoming(all_events: dict[str, list[Event]], now: datetime, upcoming_days: int) -> str:
        upcoming_texts = []
        for date in (now + timedelta(n + 1) for n in range(upcoming_days)):
            date_events = all_events.get(date.strftime('%Y-%m-%d'), [])
            if not date_events:
                continue

            date_heading = date.strftime('%A, %d %B').replace(' 0', ' ')
            date_texts = [EventsModule.__upcoming_event(e) for e in date_events]

            upcoming_texts.append(date_heading + "\n" + "\n".join(date_texts))

        return "\n\n".join(upcoming_texts)

    @staticmethod
    def __today_event(e: Event, now: datetime) -> str:
        return (
            f"<b>{e.name}</b>, "
            + ("happening <b>right now</b>" if e.start_date < now else f"starting at <b>{EventsModule.__event_time(e.start_date)}</b>")
            + (f", hosted by <b>{e.host}</b>" if e.host else "")
        )

    @staticmethod
    def __upcoming_event(e: Event) -> str:
        return (
            f"{e.name} | {EventsModule.__event_time(e.start_date)}" +
            (f" | {e.host}" if e.host else "")
        )

    @staticmethod
    def __event_time(date: datetime) -> str:
        return date.strftime('%I:%M%p').lstrip('0').replace(':00', '').lower()

    @staticmethod
    def __enumerate(lst: list[str]) -> str:
        return (', '.join(lst[:-1]) + ' and ' + lst[-1]) if len(lst) > 1 else lst[0]
