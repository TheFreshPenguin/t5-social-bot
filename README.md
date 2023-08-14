# T5 Social Bot

***A witty Telegram bot for world's friendliest hostel!***

## Getting started

The project requirements are:
- Python 3.9+
- pip

To get started on this project, you should follow these steps:
1. Clone the project to your computer
2. Run `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`
4. Create a Telegram bot for development purposes and add the token to the `.env` file
5. Run `main.py`

## How does it work?

At its core, the project uses the [python-telegram-bot library](https://docs.python-telegram-bot.org/) to interface with the [Telegram Bot API](https://core.telegram.org/bots/api). This library handles all the API calls, as well as other features such as scheduled tasks and multithreading.

The library polls Telegram for updates (messages), so it needs to be constantly running. Any updates sent while the project is not running are kept in a queue. The live project is currently hosted on Heroku. 

### Telegram

To interact with Telegram, you will need to obtain a `telegram_token` for the `.env`. To do this, you have to set up a bot that you use for your own development. This is easy - all you need to do is to talk to the Telegram account called [@BotFather](https://telegram.me/botfather) and he will walk you through the process. There is lots of helpful information in the [Telegram bot FAQ](https://core.telegram.org/bots/faq#how-do-i-create-a-bot).

### Loyverse

This is the application that manages sales at T5, along with customers, products, loyalty points, receipts and much more. Loyverse provides a [public REST API](https://developer.loyverse.com/docs) that we use to access this data.

When people pay their tabs, the sale is reported to the appropriate customer, who is correlated with a Telegram account because the Telegram username is stored in the customer "note" field. All the bar staff know how to do this, especially since they know all the customers personally :)

To get the `loyverse_token` token for the `.env` file, you need to ask Rob to give you access to the Loyverse admin panel. Then you need to go to _Integrations > Access Tokens > Telegram bot_

It's probably a good idea to do development work with Loyverse in read-only mode (`loyverse_read_only=1` in `.env`) so that you don't mess up the Loyverse data in any way. This mode will allow you to read data, but any write operations (such as saving users) will be gracefully discarded. 

### Google Sheets

We have recently started accessing data in Google Sheets through the Google API.

If you want to work with this functionality, you have to ask Rob to share the spreadsheet with you so you can see the data. The spreadsheet key (the long token in the URL) goes into the `google_spreadsheet_key` variable in `.env`.

Furthermore, you have to contact Andrei or Antoine and ask them to grant you access to the T5 Social Bot project in Google Cloud. Using the Google Cloud Console you can generate the API credentials that go into the `google_api_credentials` variable in `.env`. Please note that these credentials are a JSON string that must squashed into a single line.

## Best practices for development

The bot commands are split into modules, where each module handles one or more commands and schedules tasks where needed. If you want to add new commands, you should make a new module for them.

Because this is a bot, we want the output to be as nicely formatted as possible, so it looks like natural conversation. To deal with the complicated formatting process, only the modules themselves should produce user-friendly messages (and maybe a few helpers whose job is to specifically to format messages). The various other integrations and helpers should not "know" they're being used in a bot and should just produce generic messages. This is why it could be useful to raise custom exceptions for specific errors, so the modules can catch them and react differently to each possible error.

There are commands that should not be available to regular users, but instead only to select "master botters". These lucky few are stored in the `masters` environment variable, which is then used by the `AccessChecker` class. Ideally, this class should be used to check for access rights rather than checking for specific user names.

Since T5 is based in Bucharest, the code is hosted somewhere else in the EU, and Telegram is a global service, we need to be mindful of the timezone when working with dates. Please use the `config.timezone` variable for this.

We've learned that Telegram chatids are positive for user-to-user chats and negative for group chats. This could also change in the future. So we must make sure that the code handles both positive and negative chatids.

It's preferable that `.env` variables are only read in `main.py` and then saved to the config, as it allows strong typing and it's a single point of truth for all these values. Then the values are read from the config and passed to wherever they are needed.
