import logging
import os
import pytz

from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv

from helpers.access_checker import AccessChecker
from helpers.points import Points

from integrations.loyverse.api import LoyverseApi

from modules.help import HelpModule
from modules.points import PointsModule
from modules.raffle import RaffleModule
from modules.birthday import BirthdayModule

load_dotenv()

logger = logging.getLogger(__name__)


class MainConfig:
    def __init__(self):
        self.log_level = logging.getLevelName(os.getenv('log_level', 'INFO'))
        self.telegram_token = os.getenv('telegram_token')
        self.loyverse_token = os.getenv('loyverse_token')
        self.loyverse_read_only = bool(int(os.getenv('loyverse_read_only', 0)))
        self.birthday_chats = set([int(chatid) for chatid in os.getenv('birthday_chats', '').split(',') if chatid])
        self.birthday_points = Points(os.getenv('birthday_points', 5))
        self.timezone = pytz.timezone(os.getenv('timezone', 'Europe/Bucharest'))
        self.masters = set([username for username in os.getenv('masters', '').split(',') if username])
        self.point_masters = set([username for username in os.getenv('point_masters', '').split(',') if username])


def main() -> None:
    config = MainConfig()
    logging.basicConfig(level=config.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    loy = LoyverseApi(config.loyverse_token, read_only=config.loyverse_read_only)
    ac = AccessChecker(
        masters=config.masters,
        point_masters=config.point_masters,
    )

    modules = [
        HelpModule(),
        PointsModule(loy=loy, ac=ac),
        RaffleModule(loy=loy, ac=ac),
        BirthdayModule(
            loy=loy,
            ac=ac,
            default_chats=config.birthday_chats,
            points_to_award=config.birthday_points,
            timezone=config.timezone,
        )
    ]

    application = ApplicationBuilder().token(config.telegram_token).build()

    for module in modules:
        module.install(application)

    # Start the Bot
    logger.info('start_polling')
    application.run_polling()


if __name__ == '__main__':
    main()

