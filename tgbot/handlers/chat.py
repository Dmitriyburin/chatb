import datetime
import json
import pickle
import logging
import random

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, ContentTypes
from tgbot.keyboards import reply
from tgbot.keyboards import inline
from tgbot.handlers.channels import check_sub, required_channel
from tgbot.misc.states import EditDescription


async def chat(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    command = message.text.lower()
    logging.info(command)
    if command in ['-отн основа']:
        main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
        if not main_relation:
            await message.answer(texts['main_relation_not_exists'])
            return
        await data.edit_main_relation(message.chat.id, message.from_user.id, None)
        await message.answer(texts['main_relation_delete'])

    elif command in ['профиль', 'кто я']:
        user = await data.get_chat_user(message.chat.id, message.from_user.id)
        if not user:
            return
        coins = user['coins']
        description = user['description']
        time_registration = datetime.datetime.fromtimestamp(user['time_registration'])
        seconds = (datetime.datetime.now() - time_registration).total_seconds()
        months, days = get_months_days(int(seconds))

        main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
        if main_relation:
            user_receiver_id = main_relation['users'][1] if main_relation['users'][0] == message.from_user.id else \
                main_relation['users'][0]
            user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user

            time_registration_relation = datetime.datetime.fromtimestamp(main_relation['time_registration'])
            seconds_rel = (datetime.datetime.now() - time_registration_relation).total_seconds()
            months_rel, days_rel = get_months_days(int(seconds_rel))

            text = texts['profile_with_main_relation'].format(await get_nickname(message.from_user),
                                                              await get_nickname(user_receiver),
                                                              months_rel, days_rel, coins,
                                                              time_registration.date(), months, days, description)
        else:
            text = texts['profile_without_main_relation'].format(await get_nickname(message.from_user),
                                                                 coins,
                                                                 time_registration.date(), months, days, description)
        await message.reply(text, reply_markup=inline.edit_description(buttons, message.from_user.id))
        return

    elif command in ['баланс', 'мешок']:
        user = await data.get_chat_user(message.chat.id, message.from_user.id)
        await message.reply(texts['money'].format(await get_nickname(message.from_user), user['coins']))
        return

    elif command in ['фарма', 'фарм', 'фармить']:
        user = await data.get_chat_user(message.chat.id, message.from_user.id)
        if user['time_last_farm']:
            time_next_farm = datetime.datetime.fromtimestamp(user['time_last_farm']) + datetime.timedelta(
                hours=user['hours_to_next_farm'])

            if datetime.datetime.now() <= time_next_farm:
                seconds_to_next_farm = (time_next_farm - datetime.datetime.now()).total_seconds()
                hours, minutes = get_hours_minutes(int(seconds_to_next_farm))

                await message.answer(texts['money__cannot'].format(hours, minutes))
                return
        count_coins = random.randint(5, 50)
        await data.increase_coins(message.chat.id, message.from_user.id, count_coins)
        await data.edit_time_last_farm(message.chat.id, message.from_user.id)
        await message.answer(texts['money__success_not_subscribe'].format(await get_nickname(message.from_user),
                                                                          count_coins, user['hours_to_next_farm']))
    elif command in ['мои отн чат']:
        await message.answer(await get_user_relations(message))

    elif command in ['мои отн']:
        link = await get_link_to_relations_ls(message)
        await message.answer(texts['my_relations_ls'],
                             reply_markup=inline.list_relations_ls(buttons, message.from_user.id, link))

    elif command in ['отны', 'отны топ', 'отны чат']:
        await message.answer(texts['choose_top_relations'].format(
            await get_nickname(message.from_user)),
            reply_markup=inline.choose_top_relations(buttons, message.chat.id))

    if not message.reply_to_message and not message.entities:
        return
    elif message.reply_to_message and message.reply_to_message.from_user.id != bot.id \
            and message.reply_to_message.from_user.id != message.from_user.id:
        user_receiver = message.reply_to_message.from_user
    else:

        for en in message.entities:
            if en.type == 'mention':
                logging.info(en.as_json())
                user_receiver = en.user
                command = command.split('@')[0].strip()
                break
        else:
            return

    relation = await data.get_relation(message.chat.id, message.from_user.id, user_receiver.id)
    commands = []
    if relation:
        commands = get_commands_actions(misc, relation['hp'])
    simple_commands = [com['command'].lower() for com in misc.commands]
    user_bd = await data.get_chat_user(message.chat.id, message.from_user.id)
    if command in ['отн', '+отн', 'отношения']:
        if relation:
            await message.answer('Отношения с ним уже существуют')
            return

        await relation_request(message, user_receiver)

    elif command in ['-отн', '-отношения']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return
        await delete_relation(message, user_receiver)

    elif command in ['отн действия']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return
        link = await get_link_to_relation_actions(message, user_receiver)
        await message.answer(texts['get_relation_actions'], reply_markup=inline.go_to_link(buttons, link))

    elif command in ['отн статус']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return

        text = texts['my_relation']
        if user_bd['main_relation'] == user_receiver.id:
            text = texts['my_main_relation']

        time_registration = datetime.datetime.fromtimestamp(relation['time_registration'])
        seconds = (datetime.datetime.now() - time_registration).total_seconds()
        days = get_days(int(seconds))

        await message.answer(text.format(await get_nickname(message.from_user),
                                         await get_nickname(user_receiver),
                                         days, relation['hp']))

    elif command in ['отн основа']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return
        main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
        if main_relation:
            await message.answer(texts['main_relation_exists'])
            return

        await data.edit_main_relation(message.chat.id, message.from_user.id, user_receiver.id)
        await message.answer(texts['edit_main_relation'])

    elif command in commands:
        action = get_action_by_command(misc, relation['hp'], command)
        if relation['time_to_next_action'] and \
                datetime.datetime.now() < datetime.datetime.fromtimestamp(relation['time_to_next_action']):
            time_delta = datetime.datetime.fromtimestamp(relation['time_to_next_action']) - datetime.datetime.now()
            seconds = time_delta.total_seconds()
            hours, minutes = get_hours_minutes(int(seconds))

            num_of_action = commands.index(command)
            await message.answer(texts['cannot_make_action'].format(await get_nickname(user_receiver),
                                                                    hours, minutes, command, action['coins']),
                                 reply_markup=inline.accept_or_wait_make_action_for_money(buttons,
                                                                                          message.from_user.id,
                                                                                          user_receiver.id,
                                                                                          num_of_action))
            return
        await data.make_action(message.chat.id, message.from_user.id, user_receiver.id, action['hp'], action['time'])
        text = action['use_text'].format(await get_nickname(message.from_user),
                                         await get_nickname(user_receiver)) + '\n' + \
               texts['make_action_free'].format(action['hp'], action['time'])
        await message.answer(text)
    elif command in simple_commands:
        for com in misc.commands:
            if com['command'].lower() == command:
                await message.answer(com['use_text'].format(await get_nickname(message.from_user),
                                                            await get_nickname(user_receiver)))


async def relation_request(message: Message, user_receiver):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons
    await message.answer(
        texts['request_relation'].format(await get_nickname(message.from_user), await get_nickname(user_receiver)),
        reply_markup=inline.accept_or_refuse_relation(buttons, message.from_user.id,
                                                      user_receiver.id))


async def delete_relation(message: Message, user_receiver):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    await message.answer(
        texts['delete_relation_confirmation'].format(await get_nickname(message.from_user),
                                                     await get_nickname(user_receiver)),
        reply_markup=inline.accept_or_refuse_delete_relation(buttons, message.from_user.id,
                                                             user_receiver.id))


async def relation_callback(call: CallbackQuery):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[-1]
    user_sender_id = int(call.data.split(':')[1])
    user_receiver_id = int(call.data.split(':')[2])

    user_sender = (await bot.get_chat_member(message.chat.id, user_sender_id)).user
    user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user

    if user_receiver.id == call.message.from_id:
        if action == 'accept':
            await data.add_relation(message.chat.id, user_sender_id, user_receiver_id)
            await message.answer(
                texts['accept_relation'].format(await get_nickname(user_receiver),
                                                await get_nickname(user_sender)))

        elif action == 'refuse':
            await message.answer(
                texts['refuse_relation'].format(await get_nickname(user_receiver),
                                                await get_nickname(user_sender)))
        else:
            await call.bot.answer_callback_query(call.id)
            return
    elif user_sender.id == call.message.from_id:
        if action == 'accept_delete':
            date_relation = (await data.get_relation(message.chat.id, user_sender_id, user_receiver_id))[
                'time_registration']
            seconds = (datetime.datetime.now() - datetime.datetime.fromtimestamp(date_relation)).total_seconds()
            days, hours, minutes = get_days_hours_minutes(int(seconds))

            await data.delete_relation(message.chat.id, user_sender_id, user_receiver_id)

            await message.answer(
                texts['delete_relation'].format(await get_nickname(user_receiver),
                                                await get_nickname(user_sender),
                                                days, hours, minutes))


        elif action == 'refuse_delete':
            await message.answer('Вот и отлично')
        else:
            await call.bot.answer_callback_query(call.id)
            return
    else:
        await call.bot.answer_callback_query(call.id)
        return
    await message.delete()
    await call.bot.answer_callback_query(call.id)


async def action_callback(call: CallbackQuery):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action_ = call.data.split(':')[-1]
    user_sender_id = int(call.data.split(':')[1])
    user_receiver_id = int(call.data.split(':')[2])
    num_of_action = int(call.data.split(':')[3])
    user_sender = (await bot.get_chat_member(message.chat.id, user_sender_id)).user
    user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user

    if not (user_sender.id == message.from_user.id):
        await call.bot.answer_callback_query(call.id)
        return

    if action_ == 'accept_make':
        relation = await data.get_relation(message.chat.id, message.from_user.id, user_receiver.id)
        action = (get_action_dict(misc, relation['hp']))[num_of_action]
        user_chat = await data.get_chat_user(message.chat.id, message.from_user.id)
        user_coins = user_chat['coins']
        if user_coins - action['coins'] < 0:
            await message.answer(texts['insufficient_funds'])
            await call.bot.answer_callback_query(call.id)
            return

        await data.make_action(message.chat.id, message.from_user.id, user_receiver.id, action['hp'], action['time'],
                               free=False, coins=action['coins'])
        text = action['use_text'].format(await get_nickname(user_sender),
                                         await get_nickname(user_receiver)) + '\n' \
               + texts['make_action_not_free'].format(action['hp'], action['coins'])
        await message.answer(text)
        await message.delete()

    elif action_ == 'wait_make':
        await message.delete()


async def description_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[-1]
    user_id = int(call.data.split(':')[1])
    user = (await bot.get_chat_member(message.chat.id, user_id)).user
    if user_id != message.from_user.id:
        await call.bot.answer_callback_query(call.id)
        return

    if action == 'edit':
        await message.answer(texts['edit_description__start'].format(await get_nickname(user)),
                             reply_markup=inline.cancel(buttons, f'cancel_description:{user.id}'))
        await EditDescription.description.set()
        await state.update_data(user_id=user.id)

    if action == 'cancel':
        await message.delete()
        await state.finish()
    await call.bot.answer_callback_query(call.id)


async def list_to_chat_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    misc = bot['misc']

    user_id = int(call.data.split(':')[1])
    if user_id != message.from_user.id:
        await call.bot.answer_callback_query(call.id)
        return
    await message.answer(await get_user_relations(message))
    await message.delete()
    await call.bot.answer_callback_query(call.id)


async def top_relations_callback(call: CallbackQuery):
    bot = call.bot
    data: Database = bot['db']
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    misc = bot['misc']
    texts = misc.texts

    chat_id = int(call.data.split(':')[1])
    action = call.data.split(':')[-1]
    relations = []
    if action == 'fortress':
        relations = await data.get_best_hp_relations(chat_id)
    elif action == 'duration':
        relations = await data.get_best_time_relations(chat_id)

    if not relations:
        await call.bot.answer_callback_query(call.id)
        return

    relations_groups = [[relations[0]]]
    for i, relation in enumerate(relations):
        if i == 0:
            continue

        rel_yaml = get_relation_dict(misc, relation['hp'])
        if not len(relations_groups[-1]):
            relations_groups.append([relation])
            continue

        if rel_yaml['range'][0] <= relations_groups[-1][-1]['hp'] < rel_yaml['range'][1]:
            relations_groups[-1].append(relation)
        else:
            relations_groups.append([relation])

    logging.info(relations_groups)

    texts_relations = []
    for i, relation_group in enumerate(relations_groups):
        for j, relation in enumerate(relation_group):
            if j == 0:
                rel_yaml = get_relation_dict(misc, relation['hp'])
                texts_relations.append(rel_yaml['description'] + '\n')
            time_registration = datetime.datetime.fromtimestamp(relation['time_registration'])
            seconds = (datetime.datetime.now() - time_registration).total_seconds()
            days = get_days(int(seconds))
            user1 = (await bot.get_chat_member(message.chat.id, relation['users'][0])).user
            user2 = (await bot.get_chat_member(message.chat.id, relation['users'][1])).user
            text_relation = f'{i + +j + 1}. ' + texts['my_relation'].format(await get_nickname(user1),
                                                                            await get_nickname(user2),
                                                                            days, relation['hp'])
            texts_relations.append(text_relation)

    await message.answer('\n'.join(texts_relations))
    await call.bot.answer_callback_query(call.id)


async def edit_description(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user_id = (await state.get_data())['user_id']
    if user_id != message.from_user.id:
        return

    description = message.text
    if description:
        await data.edit_description(message.chat.id, message.from_user.id, description)
        await message.answer(texts['edit_description__success'].format(await get_nickname(message.from_user)))
        await state.finish()


async def cancel_edit_description_callback(call: CallbackQuery, state: FSMContext):
    message = call.message
    message.from_user.id = call['from']['id']
    user_id = int(call.data.split(':')[1])
    if user_id != message.from_user.id:
        await call.bot.answer_callback_query(call.id)
        return
    await message.delete()
    await state.finish()


async def help_handler(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    if message.chat.type in [types.ChatType.SUPERGROUP, types.ChatType.GROUP]:
        await message.answer(texts['help'].format(await get_nickname(message.from_user)),
                             reply_markup=inline.go_to_ls(buttons, f'https://t.me/{(await bot.get_me()).username}'))
        await message.delete()
    elif message.chat.type == types.ChatType.PRIVATE:
        await message.answer(texts['in_development'])


async def get_link_to_relation_actions(message: Message, user_receiver):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    relation = await data.get_relation(message.chat.id, message.from_user.id, user_receiver.id)
    hp = relation['hp']

    user = await data.get_user(message.from_user.id)
    free = True
    if relation['time_to_next_action'] and \
            datetime.datetime.now() < datetime.datetime.fromtimestamp(relation['time_to_next_action']):
        free = False

    if user:
        actions = get_actions(misc, hp, free=free)
        logging.info(hp)
        desc = get_relation_dict(misc, hp)['description']
        await bot.send_message(message.from_user.id, f'{desc}\n\n{actions}')
        return f'https://t.me/{(await bot.get_me()).username}'
    else:
        free = 't' if free else 'f'
        return f'https://t.me/{(await bot.get_me()).username}?start=actions_{hp}_{free}'


async def get_link_to_relations_ls(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    relations = await get_user_relations(message)

    user = await data.get_user(message.from_user.id)
    if user:
        await bot.send_message(message.from_user.id, relations)
        return f'https://t.me/{(await bot.get_me()).username}'
    else:
        return f'https://t.me/{(await bot.get_me()).username}?start=relations_{message.chat.id}'


async def get_user_relations(message, chat_id=None) -> str:
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts

    user_id = message.from_user.id
    user_bd = await data.get_chat_user(message.chat.id, user_id)
    if not chat_id:
        user = (await bot.get_chat_member(message.chat.id, user_id)).user
    else:
        user = (await bot.get_chat_member(chat_id, user_id)).user

    if chat_id:
        last_message_chat_id = message.chat.id
        message.chat.id = chat_id

    relations = await data.get_user_relations(message.chat.id, user.id)
    text_relations = [texts['my_relations'].format(await get_nickname(user))]
    for i, relation in enumerate(relations):
        partner_id = relation['users'][1] if relation['users'][0] == user.id else relation['users'][0]
        partner = (await bot.get_chat_member(message.chat.id, partner_id)).user
        time_registration = datetime.datetime.fromtimestamp(relation['time_registration'])
        seconds = (datetime.datetime.now() - time_registration).total_seconds()
        days = get_days(int(seconds))

        if user_bd['main_relation'] == partner.id:
            text_relations.append(f'{i + 1}. ' + texts['my_main_relation'].format(await get_nickname(user),
                                                                                  await get_nickname(partner),
                                                                                  days,
                                                                                  relation['hp']))
        else:
            text_relations.append(f'{i + 1}. ' + texts['my_relation'].format(await get_nickname(user),
                                                                             await get_nickname(partner),
                                                                             days,
                                                                             relation['hp']))
    if chat_id:
        message.chat.id = last_message_chat_id
    return '\n'.join(text_relations)


async def print_best_hp_relations(misc, relations):
    for rel in relations:
        for r in misc.relations:
            if r['range'][0] <= rel['hp'] < r['range'][1]:
                pass


async def get_nickname(user):
    return user.get_mention()

    # if user.username:
    #     return f'@{user.username}'
    # return user.first_name


def get_hours_minutes(seconds: int) -> tuple:
    hours = seconds // 3600
    minutes = (seconds - (hours * 3600)) // 60
    return hours, minutes


def get_days_hours_minutes(seconds: int) -> tuple:
    days = seconds // 86400
    hours = (seconds - days * 86400) // 3600
    minutes = (seconds - (hours * 3600) - (days * 86400)) // 60
    return days, hours, minutes


def get_months_days(seconds: int) -> tuple:
    months = seconds // 2592000
    days = (seconds - (months * 2592000)) // 86400
    return months, days


def get_days(seconds: int) -> int:
    return seconds // 86400


def get_actions(misc, hp: int, free=True) -> str:
    actions = []
    for r in misc.relations:
        if r['range'][0] <= hp < r['range'][1]:
            actions = r['actions']
            if free:
                actions = [action['description'] for action in actions]
            else:
                actions = [action['not_free_description'] for action in actions]

    return '\n'.join(actions)


def get_relation_dict(misc, hp) -> dict:
    for r in misc.relations:
        if r['range'][0] <= hp < r['range'][1]:
            return r


def get_action_dict(misc, hp) -> dict:
    for r in misc.relations:
        if r['range'][0] <= hp < r['range'][1]:
            return r['actions']


def get_commands_actions(misc, hp: int) -> list:
    commands = []
    for r in misc.relations:
        if r['range'][0] <= hp < r['range'][1]:
            commands = r['actions']
            commands = [command['command'] for command in commands]
    return commands


def get_action_by_command(misc, hp: int, command: str) -> dict:
    for r in misc.relations:
        if r['range'][0] <= hp < r['range'][1]:
            for action in r['actions']:
                if action['command'] == command:
                    return action


def register_chat(dp: Dispatcher):
    dp.register_message_handler(help_handler, commands=['help'], state="*")
    dp.register_callback_query_handler(relation_callback,
                                       text_contains='relation:')
    dp.register_callback_query_handler(action_callback,
                                       text_contains='action:')
    dp.register_callback_query_handler(description_callback,
                                       text_contains='description:')
    dp.register_callback_query_handler(cancel_edit_description_callback, state=EditDescription.description,
                                       text_contains='cancel_description:')
    dp.register_callback_query_handler(list_to_chat_callback,
                                       text_contains='list_to_chat:')
    dp.register_callback_query_handler(top_relations_callback,
                                       text_contains='top_relations:')

    dp.register_message_handler(edit_description, state=EditDescription.description, content_types=ContentTypes.ANY,
                                is_group=True)
    dp.register_message_handler(chat, state="*", is_group=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
