from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main(btns):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(text=btns['install']))
    markup.add(KeyboardButton(text=btns['help']), KeyboardButton(text=btns['groups']))
    return markup
