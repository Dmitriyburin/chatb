from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, \
    InlineKeyboardMarkup, ForceReply


def back(btns, callback_data):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('⬅️Назад', callback_data=callback_data))
    return markup


def back_button(callback_data):
    return InlineKeyboardButton('⬅️Назад', callback_data=callback_data)


def cancel(btns, callback_data):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Отмена', callback_data=callback_data))
    return markup


def delete_mailing(btns, message_id, ):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Удалить', callback_data=f'cancel:mailing2-{message_id}'))
    return markup


def generate_captcha():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Новая captcha', callback_data='generate_captcha'))
    return markup


def required_sub(btns, channels):
    markup = InlineKeyboardMarkup(row_width=2)
    for index, channel in enumerate(channels):
        markup.add(InlineKeyboardButton(f'Канал #{index + 1}', url=channel))
    markup.add(InlineKeyboardButton('🔎 Проверить подписку', callback_data='check_sub_call:channel'))
    markup.add(InlineKeyboardButton('🚫 Убрать рекламу', callback_data='check_sub_call:vip'))
    return markup


def ban_user(btns, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['ban'], callback_data=f'ban_user:{user_id}'))
    return markup


def yes_or_not(callback):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(InlineKeyboardButton('Да', callback_data=f'{callback}:yes'),
               InlineKeyboardButton('Нет', callback_data=f'{callback}:no'))
    return markup


def delete(callback):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton('Удалить', callback_data=f'delete:{callback}'))
    return markup


def next_or_last(month, is_next=True, is_last=True):
    markup = InlineKeyboardMarkup(row_width=2)

    next_button = None
    if is_next:
        next_button = InlineKeyboardButton('Следующий месяц', callback_data=f'month:{month + 1}')

    last_button = None
    if is_last:
        last_button = InlineKeyboardButton('Прошлый месяц', callback_data=f'month:{month - 1}')

    if is_next and is_last:
        markup.row(last_button, next_button)
    elif is_next:
        markup.row(next_button)
    elif is_last:
        markup.row(last_button)
    else:
        return None
    return markup


def unban(url):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Разбанить', url=url))
    return markup


if __name__ == '__main__':
    print(aa().to_python())
