import logging
import os
import pytz

from telegram.ext import Updater
from dotenv import load_dotenv

from helpers.loyverse import LoyverseConnector
from modules.help import HelpModule
from modules.points import PointsModule
from modules.raffle import RaffleModule
from modules.birthday import BirthdayModule

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MainConfig:
    def __init__(self):
        self.telegram_token = os.getenv('telegram_token')
        self.loyverse_token = os.getenv('loyverse_token')
        self.birthday_chats = set([int(chatid) for chatid in os.getenv('birthday_chats', '').split(',') if chatid])
        self.birthday_points = int(os.getenv('birthday_points', 5))
        self.timezone = pytz.timezone(os.getenv('timezone', 'Europe/Bucharest'))


def main() -> None:
    config = MainConfig()
    lc = LoyverseConnector(config.loyverse_token)

    modules = [
        HelpModule(),
        PointsModule(lc=lc),
        RaffleModule(lc=lc),
        BirthdayModule(
            lc=lc,
            default_chats=config.birthday_chats,
            points_to_award=config.birthday_points,
            timezone=config.timezone,
        )
    ]

    updater = Updater(config.telegram_token, use_context=True)

    for module in modules:
        module.install(updater)

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()

