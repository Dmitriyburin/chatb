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


def cancel_main(btns):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['cancel'], callback_data='cancel:main'))
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


def right_left(btns, num_of_group, chat_id, user_id, is_right=None, is_left=None):
    markup = InlineKeyboardMarkup()
    if not is_left and not is_right:
        return None

    if is_right and is_left:
        markup.row(
            InlineKeyboardButton(btns['left'], callback_data=f'relations_user:{chat_id}:{user_id}:{num_of_group - 1}'),
            InlineKeyboardButton(btns['right'], callback_data=f'relations_user:{chat_id}:{user_id}:{num_of_group + 1}'))
        return markup

    if is_right:
        markup.add(
            InlineKeyboardButton(btns['right'], callback_data=f'relations_user:{chat_id}:{user_id}:{num_of_group + 1}'))
    if is_left:
        markup.add(
            InlineKeyboardButton(btns['left'], callback_data=f'relations_user:{chat_id}:{user_id}:{num_of_group - 1}'))
    return markup


def list_actions(btns, user_sender_id, user_receiver_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['list_of_actions'],
                                    callback_data=f'list_actions:{user_sender_id}:{user_receiver_id}'))
    return markup


def fast_farm(btns, link):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['subscribe'], url=link),
        InlineKeyboardButton(btns['check'],
                             callback_data=f'check_sub_call:main_channel'))
    return markup


def add_bot_to_chat(btns, link):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['add_bot_to_chat'], url=link))
    return markup


def admin(btns):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['admin__mailing'], callback_data=f'admin:mailing'),
        InlineKeyboardButton(btns['admin__channels'], callback_data=f'admin:channels'))
    markup.row(
        InlineKeyboardButton(btns['admin__stats'], callback_data=f'admin:stats'),
        InlineKeyboardButton(btns['admin__refs'], callback_data=f'admin:refs'))
    markup.row(
        InlineKeyboardButton(btns['admin__users'], callback_data=f'admin:users'),
        InlineKeyboardButton(btns['admin__extradition'], callback_data=f'admin:extradition'))
    return markup


def mailing_choice(btns):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btns['admin__mailing__print'], callback_data=f'mailing_choice:print'))
    markup.row(
        InlineKeyboardButton(btns['admin__mailing__users'], callback_data=f'mailing_choice:users'),
        InlineKeyboardButton(btns['admin__mailing__groups'], callback_data=f'mailing_choice:groups'))
    markup.add(InlineKeyboardButton(btns['admin_mailings__add_single'], callback_data=f'mailing_choice:add_single'))
    markup.add(InlineKeyboardButton(btns['admin_mailings__print_singles'], callback_data=f'mailing_choice:print_singles'))

    return markup


def channels_choice(btns):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['admin__channels__add'], callback_data=f'channels_choice:add'),
        InlineKeyboardButton(btns['admin__channels__add_main'], callback_data=f'channels_choice:add_main'))
    markup.row(
        InlineKeyboardButton(btns['admin__channels__delete'], callback_data=f'channels_choice:delete'),
        InlineKeyboardButton(btns['admin__channels__print'], callback_data=f'channels_choice:print'))
    return markup


def refs_choice(btns):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(btns['admin__refs__add'], callback_data=f'refs_choice:add'),
        InlineKeyboardButton(btns['admin__refs__delete'], callback_data=f'refs_choice:delete'))
    markup.row(
        InlineKeyboardButton(btns['admin__refs__stats'], callback_data=f'refs_choice:stats'),
        InlineKeyboardButton(btns['admin__refs__print'], callback_data=f'refs_choice:print'))
    return markup


def extradition_choice(btns):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(btns['admin__refs__money'], callback_data=f'extradition_choice:money'))

    return markup


def our_groups(groups):
    markup = InlineKeyboardMarkup()
    for group in groups:
        markup.add(
            InlineKeyboardButton(group['button_text'], url=group['link']))
    return markup
