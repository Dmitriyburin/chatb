from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main(btns):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton(text='Reply клавиатура'))
    return markup
