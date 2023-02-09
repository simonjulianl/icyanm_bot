import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

filename = "user.csv"


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


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    if update.message.chat.type == 'group':  # Group is not supposed to join
        await update.message.reply_text("Don't be naughty!")
        return

    p = Person(data['username'], data['id'])
    p.writeToCsv()

    await update.message.reply_text("Registration Successful!")


async def send_message(data, update, context, option: str):
    message = " ".join(context.args)

    try:
        df = pd.read_csv(filename).set_index('name')
        username = data['username']
        if username not in df.index:
            await update.message.reply_text("You haven't registered yet naughty kid :(")
            return

        username = df.loc[[username]][option].values[0]
        if username is None:
            await update.message.reply_text("Be patient :( You haven't been assigned a mortal/angel yet")
            return

        try:
            chat_id = df.loc[[username]]['id'].values[0]
            await context.bot.send_message(chat_id=str(chat_id),
                                           text=f"A message from your {'angel' if option == 'mortal' else 'mortal'}: \n\n{message}")
        except Exception:
            await update.message.reply_text("Your mortal/angel is naughty, he/she hasn't registered ye")
    except Exception:
        await update.message.reply_text("Something goes wrong :(")


async def send_mortal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = get_username_id_from_update(update)
    if len(context.args) == 0:
        await update.message.reply_text("Please send a message using /sendmortal <MSG>")
        return

    await send_message(data, update, context, "mortal")


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

        chat_id_mortal = df.loc[[mortal]]['id'].values[0]
        await context.bot.send_message(chat_id=str(chat_id_mortal), text=f"Your mortal is {mortal} !!")

    df.to_csv(filename, sep=",")


if __name__ == "__main__":
    token = "6006404431:AAHTpuocTUHrQWw9hjIJVINhO4U0PO-aVhI"

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("sendmortal", send_mortal))
    application.add_handler(CommandHandler("sendangel", send_angel))
    application.add_handler(CommandHandler("generatePairing", generate_pairing))
    application.run_polling()
