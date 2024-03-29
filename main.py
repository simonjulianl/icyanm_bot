import enum
import logging
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    filename='icy_telebot_log.txt',
    filemode='a',
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

filename = "user.csv"
group_chat_id = None
initial_message_id = None
initial_message = "Let's join ICy Angel and Mortal :)\n"


class SupportedFiles(enum.Enum):
    Text = 1
    Sticker = 2


CANCEL_MESSAGE = 'c'
FIRST, SECOND = range(2)


def generate_message():
    names = pd.read_csv(filename)['name']
    message = initial_message
    for index, username in enumerate(names, start=1):
        message += f"{index}. {username}\n"
    return message


class Person:
    def __init__(self, name: str, id: str):
        self.name = name
        self.id = id
        self.angel = None
        self.mortal = None

    def writeToCsv(self):
        data = {
            'name': [self.name],
            'id': [self.id],
            'angel': [self.angel],
            'mortal': [self.mortal]
        }

        temp_df = pd.DataFrame(data=data).set_index('name')

        try:
            df = pd.read_csv(filename).set_index('name')
            if self.name in df.index:
                df.update(temp_df)
            else:
                df = pd.concat([df, temp_df])
            df.to_csv(filename, sep=',')
        except Exception as e:
            logger.critical(f"Unable to write the person because of {e}")
            temp_df.to_csv(filename, sep=",")


def get_username_id_from_update(update: Update) -> (str, str):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    return {'username': username, 'id': chat_id}


def get_id_from_group(update: Update) -> str:
    return update.message.chat.id


async def add_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global group_chat_id

    logger.info(
        f"Adding the bot to the following group {update.message.chat.title} by {update.message.from_user.first_name}"
    )
    group_chat_id = get_id_from_group(update)
    await update.message.reply_text("Adding the bot successful!")


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    if update.message.chat.type == 'group':  # Group is not supposed to join
        await update.message.reply_text("Group cannot join this game, if you want to join the AnM, please pm me :)")
        return

    logger.info(f"New registration by {update.message}")

    p = Person(data['username'], data['id'])
    p.writeToCsv()
    if any(filter(lambda x: p.name == x,
                  initial_message)):
        await update.message.reply_text("You have registered, please don't register twice >:(")
        return

    await context.bot.edit_message_text(chat_id=group_chat_id, message_id=initial_message_id,
                                        text=generate_message())
    await update.message.reply_text("Registration Successful!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_type = update.message.chat.type
    if message_type == "private":
        logger.info(f"The following chat {update.message.chat.first_name} is trying to start the message in pm")
        await update.message.reply_text("You cannot start this bot in private message :)")
        return

    await add_to_group(update, context)
    global initial_message_id
    result = await context.bot.send_message(chat_id=group_chat_id, text=generate_message())
    initial_message_id = result.message_id


async def send_message(data, update, context, option: str):
    try:
        df = pd.read_csv(filename).set_index('name')
        my_username = data['username']
        if my_username not in df.index:
            await update.message.reply_text("You haven't registered yet naughty kid :(")
            return

        other_username = df.loc[[my_username]][option].values[0]
        if pd.isnull(other_username):
            await update.message.reply_text("Be patient :( You haven't been assigned a mortal/angel yet")
            return

        try:
            await update.message.reply_text("Message sent!")
            preamble_message = f"@{other_username if option == 'mortal' else my_username} {'your angel sent' if option == 'mortal' else 'sent their angel'}"
            if data[SupportedFiles.Text] is not None:
                message = data[SupportedFiles.Text]
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=f"{preamble_message} a message: \n\n{message}"
                )
            if data[SupportedFiles.Sticker] is not None:
                sticker = data[SupportedFiles.Sticker]
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=f"{preamble_message} a sticker \n"
                )
                await context.bot.send_sticker(
                    chat_id=group_chat_id,
                    sticker=sticker,
                )

        except Exception as e:
            logger.critical(f"Unable to send the message because of {e}")
            await update.message.reply_text("Seems that I cannot find the group :(, please register your group")
    except Exception as e:
        logger.critical(f"Unable to send message because of {e}")
        await update.message.reply_text("Something goes wrong :(")


async def start_send_mortal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Please enter your message for your mortal (type '{CANCEL_MESSAGE}' to cancel)")
    return FIRST


async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    data[SupportedFiles.Sticker] = update.message.sticker
    data[SupportedFiles.Text] = update.message.text
    if data[SupportedFiles.Text] == CANCEL_MESSAGE:
        await update.message.reply_text("Message cancelled :)")
        return ConversationHandler.END

    if all([(data[f] is None) for f in SupportedFiles]):
        await update.message.reply_text("Unsupported message type :), please request @simonjulianl for extra features")
    else:
        await send_message(data, update, context, "mortal")
    return ConversationHandler.END


async def generate_pairing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_csv(filename).set_index("name")
    names = list(df.index)
    # Generating a random derangement for the names https://en.wikipedia.org/wiki/Derangement
    import random

    def derangement(lst):
        copy = lst[:]
        while any(x == y for x, y in zip(copy, lst)):
            random.shuffle(lst)

    ori_names = names[:]
    derangement(names)  # ori name is the angel of derangement
    for angel, mortal in zip(ori_names, names):
        df.loc[angel, 'mortal'] = mortal
        df.loc[mortal, 'angel'] = angel

        angel_id_mortal = df.loc[[angel]]['id'].values[0]
        await context.bot.send_message(chat_id=str(angel_id_mortal), text=f"Your mortal is {mortal} !!")

    df.to_csv(filename, sep=",")


async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("To use me\n1. Add me to the group that you wanna play on\n"
                                    "2. call /start in that group\n"
                                    "3. For each player, send /register in private message to the bot!\n"
                                    "4. Wait to be paired up >:(\n"
                                    "5. Send each other well wishes using /sendmortal to send to your angel and mortal respectively!!\n\n"
                                    "Alrighty, have fun bois and gals :)")


if __name__ == "__main__":
    # token = "6249910789:AAFheDH7BAyhsxDEMs_njrakG4cqHxivA7I"  # my test boot
    token = "6125997203:AAFXBXfkMEWRR4LCSp26p5LGTUU9gn4hPZw" # the real icy anm bot

    try:
        logger.info("Starting the bot")
        application = Application.builder().token(token).build()

        application.add_handler(CommandHandler("help", help_message))
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("register", register))
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('sendmortal', start_send_mortal)],
            states={
                FIRST: [MessageHandler(filters.ALL & ~filters.COMMAND, get_message)]
            },
            fallbacks=[]
        ))
        application.add_handler(CommandHandler("generatePairing", generate_pairing))
        application.run_polling()
    except Exception as e:
        logger.critical(f"Restarting the app because of {e}")
