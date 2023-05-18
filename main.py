import logging
import os

from telegram import Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, KeyboardButton,ReplyKeyboardMarkup, ReplyMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

logger = logging.getLogger(__name__)

# telegram token
if os.environ.get('is_prod') == 'True':
    TELEGRAM_TOKEN = os.environ['telegram_token']
else:
    with open('secret.txt', 'r') as file:
        TELEGRAM_TOKEN = file.read()

# Store bot screaming status
screaming = False

# Pre-assign menu text
MAIN_MENU = "What do you want to do?"
SIGNED_UP_STATUS = "Cool! You signed up. Now it's just a matter of you showing up on time. Enjoy!\n" \
                   "The following community members are coming:\n"
# Pre-assign button text
NEXT_BUTTON = "Next"
BACK_BUTTON = "Back"
TUTORIAL_BUTTON = "Tutorial"

SIGN_UP_POKER_BUTTON = "Sign up for this Sunday's Poker Night ♦♠"
CREATE_TRIVIA_TEAM = "Create a Trivia Team for this Friday's Trivia 🤓✒"
CHECK_POINTS = "Check your Community Points balance 📄"

# Build keyboards
FIRST_MENU_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(NEXT_BUTTON, callback_data=NEXT_BUTTON)
]])
SECOND_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(BACK_BUTTON, callback_data=BACK_BUTTON)],
    [InlineKeyboardButton(TUTORIAL_BUTTON, url="https://core.telegram.org/bots/api")]
])

MAIN_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(SIGN_UP_POKER_BUTTON, callback_data=SIGN_UP_POKER_BUTTON)],
    [InlineKeyboardButton(CREATE_TRIVIA_TEAM, callback_data=CREATE_TRIVIA_TEAM)],
    [InlineKeyboardButton(CHECK_POINTS, callback_data=CHECK_POINTS)]
])

#Poker participants
poker_participants = []

def echo(update: Update, context: CallbackContext) -> None:
    """
    This function would be added to the dispatcher as a handler for messages coming from the Bot API
    """

    # Print to console
    print(f'{update.message.from_user.first_name} wrote {update.message.text}')

    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Welcome to T5 Social !\n"
        "BeeDeeBeeBoop 🤖 Hi I'm T5 Social's Telegram bot. With me, you can create a team for Trivia Night, book a spot \n"
        "for the Poker Tournament on Sunday, check you community points and many more!!\n"
        "Note that I am still a Demo. Many updates to come ❤️"
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

def start(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text="Welcome to T5 Social !\n"
             "BeeDeeBeeBoop 🤖 Hi I'm T5 Social's Telegram bot. With me, you can create a team for Trivia Night, book a spot \n"
             "for the Poker Tournament on Sunday, check you community points and many more!!\n"
             "Note that I am still a Demo. Many updates to come ❤️"
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

def scream(update: Update, context: CallbackContext) -> None:
    """
    This function handles the /scream command
    """

    global screaming
    screaming = True


def whisper(update: Update, context: CallbackContext) -> None:
    """
    This function handles /whisper command
    """

    global screaming
    screaming = False


def menu(update: Update, context: CallbackContext) -> None:
    """
    This handler sends a menu with the inline buttons we pre-assigned above
    """

    context.bot.send_message(
        update.message.from_user.id,
        FIRST_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=FIRST_MENU_MARKUP
    )


def button_tap(update: Update, context: CallbackContext) -> None:
    """
    This handler processes the inline buttons on the menu
    """

    data = update.callback_query.data
    text = ''
    markup = None

    if data == NEXT_BUTTON:
        text = SECOND_MENU
        markup = SECOND_MENU_MARKUP
    elif data == BACK_BUTTON:
        text = FIRST_MENU
        markup = FIRST_MENU_MARKUP
    elif data == SIGN_UP_POKER_BUTTON:
        if update.callback_query.from_user.username in poker_participants:
            text = "You already signed up!"
        else:
            poker_participants.append(update.callback_query.from_user.username)
            text = SIGNED_UP_STATUS+'\n -'.join(map(str, poker_participants))

        markup = MAIN_MENU_MARKUP

    # Close the query to end the client-side loading animation
    update.callback_query.answer()

    context.bot.send_message(
        chat_id=update.callback_query.from_user.id,
        text=text,
    )

    context.bot.send_message(
        chat_id=update.callback_query.from_user.id,
        text=MAIN_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=MAIN_MENU_MARKUP
    )



def main() -> None:
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("scream", scream))
    dispatcher.add_handler(CommandHandler("whisper", whisper))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("start", start))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_tap))

    # Echo any message that is not a command
    dispatcher.add_handler(MessageHandler(~Filters.command, echo))

    # Start the Bot
    logging.info('start_polling')
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
