import logging
import os

from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, KeyboardButton,ReplyKeyboardMarkup, ReplyMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from prompt_parser import parse

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# telegram token
if os.environ.get('is_prod') == 'True':
    TELEGRAM_TOKEN = os.environ['telegram_token']
else:
    with open('secret.txt', 'r') as file:
        TELEGRAM_TOKEN = file.read()

prompts = parse("resources/prompts.txt")

# menu navigation state
STATE = None
# Pre-assign menu text
MAIN_MENU = prompts.get("main_menu")
SIGNED_UP_STATUS = prompts.get("signed_up_status")

# Pre-assign button text
SIGN_UP_POKER_BUTTON = prompts.get("sign_up_poker_button")
CREATE_TRIVIA_TEAM = prompts.get("create_trivia_team")
CHECK_POINTS = prompts.get("check_points")
TRIVIA_HALL_OF_FAME = prompts.get("trivia_hall_of_fame")
MANAGE_TRIVIA_TEAM = prompts.get("manage_trivia_teams")
SEE_TEAMS = prompts.get("see_your_teams")
CHECK_TRVIA_SCORE = prompts.get("check_trivia_score")
GO_BACK_MAIN_MENU = prompts.get("go_back_main_menu")

# Build keyboards
MAIN_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(TRIVIA_HALL_OF_FAME, callback_data=TRIVIA_HALL_OF_FAME)],
    [InlineKeyboardButton(MANAGE_TRIVIA_TEAM, callback_data=MANAGE_TRIVIA_TEAM)],
    [InlineKeyboardButton(SIGN_UP_POKER_BUTTON, callback_data=SIGN_UP_POKER_BUTTON)],
    [InlineKeyboardButton(CHECK_POINTS, callback_data=CHECK_POINTS)]
])

MANAGE_TRIVIA_TEAMS_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(CREATE_TRIVIA_TEAM, callback_data=CREATE_TRIVIA_TEAM)],
    [InlineKeyboardButton(SEE_TEAMS, callback_data=SEE_TEAMS)],
    # [InlineKeyboardButton(CHECK_TRVIA_SCORE, callback_data=CHECK_TRVIA_SCORE)],
    [InlineKeyboardButton(GO_BACK_MAIN_MENU, callback_data=GO_BACK_MAIN_MENU)]
])


#Poker participants
poker_participants = []

def start(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=prompts.get("welcome")
    )

    with open('events_of_the_week.txt', 'r') as file:
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=file.read(),
            parse_mode="MarkdownV2"
        )

    context.bot.send_message(
        update.message.from_user.id,
        MAIN_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=MAIN_MENU_MARKUP
    )
def reply(update, context):
    global STATE
    user_input = update.message.text
    if STATE == CREATE_TRIVIA_TEAM:
        context.bot.send_message(
            update.message.from_user.id,
            text="team created",
            parse_mode="MarkdownV2",
            reply_markup=MANAGE_TRIVIA_TEAMS_MENU_MARKUP
        )
        STATE = None

def button_tap(update: Update, context: CallbackContext) -> None:
    """
    This handler processes the inline buttons on the menu
    """
    global STATE

    data = update.callback_query.data
    text = ''
    markup = None

    logger.debug(f'{update.callback_query.from_user.username} tapped on {data}')

    if data == SIGN_UP_POKER_BUTTON:
        if update.callback_query.from_user.username in poker_participants:
            text = "You already signed up"
        else:
            poker_participants.append(update.callback_query.from_user.username)
            text = SIGNED_UP_STATUS+'\n \- '+'\n \- '.join(map(str, poker_participants))

        markup = MAIN_MENU_MARKUP
    elif data == CHECK_POINTS:
        text = "you have *55* Community Points left to spend at the bar"
        markup = MAIN_MENU_MARKUP
    elif data == TRIVIA_HALL_OF_FAME:
        context.bot.send_photo(
            chat_id=update.callback_query.from_user.id,
            photo="https://i.ibb.co/y0QtMQY/img.png",
        )
        text = "Compete with a registered team to be on the Hall Of Fame"
        markup = MAIN_MENU_MARKUP

    elif data == MANAGE_TRIVIA_TEAM:
        text = "this is where you manage your trivia teams"
        markup = MANAGE_TRIVIA_TEAMS_MENU_MARKUP
    elif data == GO_BACK_MAIN_MENU:
        text = "back to the main menu"
        markup = MAIN_MENU_MARKUP
    elif data == CREATE_TRIVIA_TEAM:
        text = "write down your team's name"
        markup = None
        STATE = CREATE_TRIVIA_TEAM
    # Close the query to end the client-side loading animation
    update.callback_query.answer()

    context.bot.send_message(
        chat_id=update.callback_query.from_user.id,
        text=text,
        parse_mode="MarkdownV2",
    )

    if markup:
        context.bot.send_message(
            chat_id=update.callback_query.from_user.id,
            text=MAIN_MENU,
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )



def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("start", start))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_tap))

    # Echo any message that is not a command
    dispatcher.add_handler(MessageHandler(~Filters.command, reply))

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
