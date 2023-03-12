import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, Updater

filename = "user.csv"
group_chat_id = None
initial_message_id = None
initial_message = ["Let's join ICy Angel and Mortal :)"]

FIRST, SECOND = range(2)

def generate_message():
    global initial_message
    message = initial_message[0] + "\n"
    for index, username in enumerate(initial_message[1:], start=1):
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
        except Exception:
            temp_df.to_csv(filename, sep=",")


def get_username_id_from_update(update: Update) -> (str, str):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    return {'username': username, 'id': chat_id}


def get_id_from_group(update: Update) -> str:
    return update.message.chat.id


async def add_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global group_chat_id
    group_chat_id = get_id_from_group(update)
    await update.message.reply_text("Adding the bot successful!")


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    if update.message.chat.type == 'group':  # Group is not supposed to join
        await update.message.reply_text("Group cannot join this game, don't be naughty!")
        return

    p = Person(data['username'], data['id'])
    p.writeToCsv()
    if any(filter(lambda x: p.name == x,
                  initial_message)):
        await update.message.reply_text("You have registered, please don't register twice >:(")
        return

    initial_message.append(p.name)
    await context.bot.edit_message_text(chat_id=group_chat_id, message_id=initial_message_id,
                                        text=generate_message())
    await update.message.reply_text("Registration Successful!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await add_to_group(update, context)
    global initial_message_id
    result = await context.bot.send_message(chat_id=group_chat_id, text=generate_message())
    initial_message_id = result.message_id


async def send_message(data, update, context, message, option: str):
    #message = " ".join(context.args)

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
            #await context.bot.send_message(chat_id=group_chat_id,
                                            #text=f"@{other_username if option == 'mortal' else my_username} {'your angel sent' if option == 'mortal' else 'sent their angel'} a message: \n\n{message}")
            await update.message.reply_text("Message sent!")
            await context.bot.send_message(chat_id=group_chat_id,
                                            text=f"@{other_username if option == 'mortal' else my_username} {'your angel sent' if option == 'mortal' else 'sent their angel'} a message: \n\n{message}")
                                           
        except Exception:
            await update.message.reply_text("Seems that I cannot find the group :(, please register your group")
    except Exception as e:
        print(e)
        await update.message.reply_text("Something goes wrong :(")


#async def send_mortal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #data = get_username_id_from_update(update)
    #if len(context.args) == 0:
        #await update.message.reply_text("Please send a message using /sendmortal <MSG>")
        #return

    #await send_message(data, update, context, "mortal")

async def start_send_mortal(update:Update, context: ContextTypes.DEFAULT_TYPE)-> None:
    await update.message.reply_text("Please enter your message for your mortal")
    return FIRST

async def get_message(update:Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    message = update.message.text
    await send_message(data,update,context,message,"mortal")
    return ConversationHandler.END


async def send_angel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    if len(context.args) == 0:
        await update.message.reply_text("Please send a message using /sendangel <MSG>")
        return

    await send_message(data, update, context, "angel")


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
                                    "5. Send each other well wishes using /sendangel and /sendmortal to send to your angel and mortal respectively!!\n\n"
                                    "Alrighty, have fun bois and gals :)")


if __name__ == "__main__":
    token = "6006404430:AAHTpuocTUHrQWw9hjIJVINhO4U0PO-aVhI"

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("help", help_message))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    #application.add_handler(CommandHandler("sendmortal", send_mortal))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('sendmortal',start_send_mortal)],
        states={
            FIRST:[MessageHandler(filters.TEXT & ~filters.COMMAND,get_message)]
        },
        fallbacks=[]
    ))
    #application.add_handler(CommandHandler("sendangel", send_angel))
    application.add_handler(CommandHandler("generatePairing", generate_pairing))
    application.run_polling()
