import json
import pickle

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
    markup.add(InlineKeyboardButton(btns['cancel'], callback_data=callback_data))
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


def accept_or_refuse_relation(btns, user_sender, user_receiver):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['accept_relation'],
                             callback_data=f'relation:{user_sender}:{user_receiver}:accept'),
        InlineKeyboardButton(btns['refuse_relation'],
                             callback_data=f'relation:{user_sender}:{user_receiver}:refuse'))
    return markup


def accept_or_refuse_delete_relation(btns, user_sender, user_receiver):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['accept_delete_relation'],
                             callback_data=f'relation:{user_sender}:{user_receiver}:accept_delete'),
        InlineKeyboardButton(btns['refuse_delete_relation'],
                             callback_data=f'relation:{user_sender}:{user_receiver}:refuse_delete'))
    return markup


def go_to_link(btns, link):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['go_to_link'], url=link))
    return markup


def go_to_ls(btns, link):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['go_to_ls'], url=link))
    return markup


def accept_or_wait_make_action_for_money(btns, user_sender, user_receiver, num_of_action):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['accept_make_action_for_money'],
                             callback_data=f'action:{user_sender}:{user_receiver}:{num_of_action}:accept_make'),
        InlineKeyboardButton(btns['wait_to_make_action_for_money'],
                             callback_data=f'action:{user_sender}:{user_receiver}:{num_of_action}:wait_make'))
    return markup


def edit_description(btns, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['edit_description'], callback_data=f'description:{user_id}:edit'))
    return markup


def list_relations_ls(btns, user_id, link):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['go_to_link'], url=link),
        InlineKeyboardButton(btns['list_to_chat'],
                             callback_data=f'list_to_chat:{user_id}'))
    return markup


def done(btns, callback):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['done'], callback_data=callback))
    return markup


def choose_top_relations(btns, chat_id):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['fortress'], callback_data=f'top_relations:{chat_id}:fortress'),
        InlineKeyboardButton(btns['duration'],
                             callback_data=f'top_relations:{chat_id}:duration'))
    return markup
