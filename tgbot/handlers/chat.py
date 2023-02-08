import datetime
import json
import uvloop
import logging
import random

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BotBlocked
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

    simple_commands = [com['command'].lower() for com in misc.commands]
    all_command_actions = get_all_actions(misc)
    all_commands = ['-отн основа'] + ['профиль', 'кто я'] + ['баланс', 'мешок'] + ['фарма', 'ферма', 'фарм',
                                                                                   'фармить'] + [
                       'мои отн чат'] + ['мои отн'] + ['отны', 'отны топ', 'отны чат'] + ['отн', '+отн', 'отношения',
                                                                                          '/otn'] + [
                       '-отн', '-отношения'] + ['отн действия'] + ['отн статус'] + [
                       'отн основа'] + ['профиль', 'кто я', 'кто ты'] + simple_commands + all_command_actions

    if command in all_commands or message.text.split('@')[0].lower().strip() in all_commands or \
            any([command.startswith(c) for c in simple_commands]):
        await data.add_chat_if_not_exists(message.chat.id)
        await data.add_user_if_not_exists(message.chat.id, message.from_user.id)
    else:
        return

    if command in ['-отн основа']:
        main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
        if not main_relation:
            await message.answer(texts['main_relation_not_exists'])
            return
        await data.edit_main_relation(message.chat.id, message.from_user.id, None)
        await message.answer(texts['main_relation_delete'])

    elif command in ['профиль', 'кто я'] and not message.reply_to_message:
        await print_profile(message)
        return

    elif command in ['баланс', 'мешок']:
        user = await data.get_user_chats(message.from_user.id)

        await message.reply(texts['money'].format(await get_nickname(message.from_user), user['coins']))
        return

    elif command in ['фарма', 'фарм', 'фармить', 'ферма']:
        user_chats = await data.get_user_chats(message.from_user.id)
        if user_chats['time_last_farm']:
            time_next_farm = datetime.datetime.fromtimestamp(user_chats['time_last_farm']) + datetime.timedelta(
                hours=user_chats['hours_to_next_farm'])

            if datetime.datetime.now() <= time_next_farm:
                seconds_to_next_farm = (time_next_farm - datetime.datetime.now()).total_seconds()
                hours, minutes = get_hours_minutes(int(seconds_to_next_farm))
                text = texts['money__cannot'].format(hours, minutes)
                if user_chats['hours_to_next_farm'] == 4:
                    try:
                        link = await get_link_to_fast_farm(message)
                        text = texts['money__cannot_not_subscribe'].format(hours, minutes, link)
                    except BotBlocked as e:
                        link = await get_link_to_fast_farm(message, start=True)
                        text = texts['money__cannot_not_subscribe'].format(hours, minutes, link)

                await message.answer(text, disable_web_page_preview=True)
                return
        count_coins = random.randint(5, 50)
        text = texts['money__success'].format(await get_nickname(message.from_user),
                                              count_coins, user_chats['hours_to_next_farm'])
        if user_chats['hours_to_next_farm'] == 4:
            try:
                link = await get_link_to_fast_farm(message)
                text = texts['money__success_not_subscribe'].format(await get_nickname(message.from_user),
                                                                    count_coins, user_chats['hours_to_next_farm'],
                                                                    link)
            except BotBlocked as e:
                link = await get_link_to_fast_farm(message, start=True)
                text = texts['money__success_not_subscribe'].format(await get_nickname(message.from_user),
                                                                    count_coins, user_chats['hours_to_next_farm'],
                                                                    link)

        await data.increase_coins(message.from_user.id, count_coins)
        await data.edit_time_last_farm(message.from_user.id)
        await message.answer(text, disable_web_page_preview=True)
    elif command in ['мои отн чат']:
        await print_user_relations(message, 0)

    elif command in ['мои отн']:
        try:
            link = await get_link_to_relations_ls(message)
            await message.answer(texts['my_relations_ls'],
                                 reply_markup=inline.list_relations_ls(buttons, message.from_user.id, link))
        except BotBlocked:
            link = await get_link_to_relations_ls(message, start=True)
            await message.answer(texts['my_relations_ls'],
                                 reply_markup=inline.list_relations_ls(buttons, message.from_user.id, link))

    elif command in ['отны', 'отны топ', 'отны чат']:
        relations = await data.get_best_hp_relations(message.chat.id)
        if not relations:
            await message.answer(texts['relations_not_exists'])
            return
        await message.answer(texts['choose_top_relations'].format(
            await get_nickname(message.from_user)),
            reply_markup=inline.choose_top_relations(buttons, message.chat.id))

    main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
    is_main_relation_command = False
    if not message.reply_to_message and not message.entities and not main_relation:
        return
    elif message.reply_to_message and message.reply_to_message.from_user.id != bot.id \
            and message.reply_to_message.from_user.id != message.from_user.id:
        user_receiver = message.reply_to_message.from_user
    elif message.entities:
        for en in message.entities:
            if en.type == 'mention':
                username = message.text.split('@')[1].strip()
                user_receiver_id = await data.get_id_by_username(username)
                print(user_receiver_id)
                user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user
                command = message.text.split('@')[0].lower().strip()
                break
        else:
            return
    elif main_relation:
        user_receiver_id = main_relation
        user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user
        is_main_relation_command = True
    else:
        return

    relation = await data.get_relation(message.chat.id, message.from_user.id, user_receiver.id)
    commands = []
    if relation:
        commands = get_commands_actions(misc, relation['hp'])

    if command not in (
            ['отн', '+отн', 'отношения', '/otn'] + ['-отн', '-отношения'] + ['отн действия'] + ['отн статус'] + [
        'отн основа'] + ['профиль', 'кто я', 'кто ты'] + commands + simple_commands) and not any(
        [command.startswith(c) for c in simple_commands]):
        return
    else:
        await data.add_user_if_not_exists(message.chat.id, user_receiver.id)
        await data.add_user_chats_if_not_exists(user_receiver.id, username=user_receiver.username)
        await data.update_username_if_update(user_receiver.id, username=user_receiver.username)

    user_bd = await data.get_chat_user(message.chat.id, message.from_user.id)
    if command in ['отн', '+отн', 'отношения', '/otn'] and not is_main_relation_command:
        if relation:
            await message.answer('Отношения с ним уже существуют')
            return

        await relation_request(message, user_receiver)

    elif command in ['-отн', '-отношения'] and not is_main_relation_command:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return
        await delete_relation(message, user_receiver)

    elif command in ['отн действия']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return

        try:
            link = await get_link_to_relation_actions(message, user_receiver)
            await message.answer(texts['get_relation_actions'], reply_markup=inline.go_to_link(buttons, link))
        except BotBlocked as e:
            link = await get_link_to_relation_actions(message, user_receiver, start=True)
            await message.answer(texts['get_relation_actions__cannot'], reply_markup=inline.go_to_link(buttons, link))

    elif command in ['отн статус']:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return

        text = texts['relation_status']
        if user_bd['main_relation'] == user_receiver.id:
            text = texts['relation_status']

        time_registration = datetime.datetime.fromtimestamp(relation['time_registration'])
        seconds = (datetime.datetime.now() - time_registration).total_seconds()
        days, hours = get_days_hours(int(seconds))
        relation_yaml = get_relation_dict(misc, relation['hp'])
        await message.answer(text.format(await get_nickname(message.from_user),
                                         await get_nickname(user_receiver),
                                         days, hours, relation_yaml['description'],
                                         relation['hp'], relation_yaml['range'][1]),
                             reply_markup=inline.list_actions(buttons, message.from_user.id, user_receiver.id))

    elif command in ['отн основа'] and not is_main_relation_command:
        if not relation:
            await message.answer('Отношений с ним не существует')
            return
        main_relation = await data.get_main_relation(message.chat.id, message.from_user.id)
        if main_relation:
            await message.answer(texts['main_relation_exists'])
            return

        await data.edit_main_relation(message.chat.id, message.from_user.id, user_receiver.id)
        await message.answer(texts['edit_main_relation'])

    elif command in ['профиль', 'кто я', 'кто ты'] and not is_main_relation_command:
        await print_profile(message, partner=user_receiver)

    elif command in commands:
        action = get_action_by_command(misc, relation['hp'], command)
        if relation['time_to_next_action'] and \
                datetime.datetime.now() < datetime.datetime.fromtimestamp(relation['time_to_next_action']):
            time_delta = datetime.datetime.fromtimestamp(relation['time_to_next_action']) - datetime.datetime.now()
            seconds = time_delta.total_seconds()
            hours, minutes = get_hours_minutes(int(seconds))

            num_of_action = commands.index(command)
            await message.answer(texts['cannot_make_action'].format(await get_nickname(message.from_user),
                                                                    hours, minutes, action['coins']),
                                 reply_markup=inline.accept_or_wait_make_action_for_money(buttons,
                                                                                          message.from_user.id,
                                                                                          user_receiver.id,
                                                                                          num_of_action))
            return

        relation_yaml_old = get_relation_dict(misc, relation['hp'])
        await data.make_action(message.chat.id, message.from_user.id, user_receiver.id, action['hp'], action['time'])
        text = action['use_text'].format(await get_nickname(message.from_user),
                                         await get_nickname(user_receiver)) + '\n' + \
               texts['make_action_free'].format(action['hp'], action['time'])
        await message.answer(text)

        relation_yaml_new = get_relation_dict(misc, relation['hp'] + action['hp'])
        if relation_yaml_old != relation_yaml_new:
            await message.answer(texts['new_level'].format(relation_yaml_new['description']))

    elif any([command.startswith(c) for c in simple_commands]):
        for com in misc.commands:
            if com['command'].lower() == command:
                await message.answer(com['use_text'].format(await get_nickname(message.from_user),
                                                            await get_nickname(user_receiver)))
            elif command.startswith(com['command'].lower()):
                with_words = ' '.join(command.split()[len(com['command'].split()):])
                await message.answer(
                    f"{com['use_text'].format(await get_nickname(message.from_user), await get_nickname(user_receiver))}\nСо словами: {with_words}")


async def relation_request(message: Message, user_receiver):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons
    await message.answer(
        texts['request_relation'].format(await get_nickname(user_receiver), await get_nickname(message.from_user)),
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
            link = await get_link_to_relation_actions(message, user_receiver, user_sender=user_sender, start=True)
            await message.answer(
                texts['accept_relation'].format(await get_nickname(user_receiver),
                                                await get_nickname(user_sender),
                                                link), disable_web_page_preview=True)

        elif action == 'refuse':
            await message.answer(
                texts['refuse_relation'].format(await get_nickname(user_sender),
                                                await get_nickname(user_receiver)))
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
            await message.delete()
            await call.bot.answer_callback_query(call.id)
            return

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
        chats_user = await data.get_user_chats(message.from_user.id)
        user_coins = chats_user['coins']
        if user_coins - action['coins'] < 0:
            await message.answer(texts['insufficient_funds'])
            await call.bot.answer_callback_query(call.id)
            return

        relation_yaml_old = get_relation_dict(misc, relation['hp'])
        await data.make_action(message.chat.id, message.from_user.id, user_receiver.id, action['hp'], action['time'],
                               free=False, coins=action['coins'])
        text = action['use_text'].format(await get_nickname(user_sender),
                                         await get_nickname(user_receiver)) + '\n' \
               + texts['make_action_not_free'].format(action['hp'], action['coins'])
        await message.answer(text)
        relation_yaml_new = get_relation_dict(misc, relation['hp'] + action['hp'])
        if relation_yaml_old != relation_yaml_new:
            await message.answer(texts['new_level'].format(relation_yaml_new['description']))
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


async def list_actions_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user_sender_id = int(call.data.split(':')[1])
    user_receiver_id = int(call.data.split(':')[2])

    if user_sender_id != message.from_user.id:
        await call.bot.answer_callback_query(call.id)
        return

    user_sender = (await bot.get_chat_member(message.chat.id, user_sender_id)).user
    user_receiver = (await bot.get_chat_member(message.chat.id, user_receiver_id)).user

    try:
        link = await get_link_to_relation_actions(message, user_receiver, user_sender=user_sender)
        await message.answer(texts['get_relation_actions'], reply_markup=inline.go_to_link(buttons, link))
    except BotBlocked as e:
        link = await get_link_to_relation_actions(message, user_receiver, user_sender=user_sender, start=True)
        await message.answer(texts['get_relation_actions__cannot'], reply_markup=inline.go_to_link(buttons, link))
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
    await print_user_relations(message, 0, message.from_user.id, edit=False, send_message=False)
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

    texts_relations = []
    if action == 'fortress':
        texts_relations.append(f"{texts['fortress']}\n")
    elif action == 'duration':
        texts_relations.append(f"{texts['duration']}\n")

    count = 1
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
            text_relation = f'{count}. ' + texts['my_relation'].format(await get_nickname(user1),
                                                                       await get_nickname(user2),
                                                                       days, relation['hp'])
            texts_relations.append(text_relation)
            count += 1

    await message.answer('\n'.join(texts_relations))
    await message.delete()
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


async def print_profile(message, partner=None):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = message.from_user
    if partner:
        user = partner

    user_db = await data.get_chat_user(message.chat.id, user.id)
    chats_user = await data.get_user_chats(user.id)
    if not user_db:
        return
    coins = chats_user['coins']
    description = user_db['description']
    time_registration = datetime.datetime.fromtimestamp(user_db['time_registration'])
    seconds = (datetime.datetime.now() - time_registration).total_seconds()
    months, days = get_months_days(int(seconds))

    main_relation = await data.get_main_relation(message.chat.id, user.id)
    if main_relation:
        user_receiver = (await bot.get_chat_member(message.chat.id, main_relation)).user
        relation = await data.get_relation(message.chat.id, user.id, user_receiver.id)
        time_registration_relation = datetime.datetime.fromtimestamp(relation['time_registration'])
        seconds_rel = (datetime.datetime.now() - time_registration_relation).total_seconds()
        months_rel, days_rel = get_months_days(int(seconds_rel))

        text = texts['profile_with_main_relation'].format(await get_nickname(user),
                                                          await get_nickname(user_receiver),
                                                          months_rel, days_rel, coins,
                                                          time_registration.date(), months, days, description)
    else:
        text = texts['profile_without_main_relation'].format(await get_nickname(user),
                                                             coins,
                                                             time_registration.date(), months, days, description)

    markup = inline.edit_description(buttons, user.id)
    if partner:
        markup = None
    await message.reply(text, reply_markup=markup)


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
        await message.answer(texts['help_private'])


async def get_link_to_relation_actions(message: Message, user_receiver, start=False, user_sender=None):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    if not user_sender:
        user_sender = message.from_user

    relation = await data.get_relation(message.chat.id, user_sender.id, user_receiver.id)
    hp = relation['hp']

    user_db = await data.get_user(user_sender.id)
    free = True
    if relation['time_to_next_action'] and \
            datetime.datetime.now() < datetime.datetime.fromtimestamp(relation['time_to_next_action']):
        free = False

    if user_db and not start:
        actions = get_actions(misc, hp, free=free)
        desc = get_relation_dict(misc, hp)['description']
        await bot.send_message(user_sender.id, f'{desc}\n\n{actions}')
        return f'https://t.me/{(await bot.get_me()).username}'
    elif not user_db or start:
        free = 't' if free else 'f'
        return f'https://t.me/{(await bot.get_me()).username}?start=actions_{hp}_{free}'


async def get_link_to_relations_ls(message: Message, start=False) -> str:
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = await data.get_user(message.from_user.id)
    if user and not start:
        await print_user_relations(message, 0, user_id=message.from_user.id, edit=False, send_message=True)
        return f'https://t.me/{(await bot.get_me()).username}'
    elif not user or start:
        return f'https://t.me/{(await bot.get_me()).username}?start=relations_{message.chat.id}'


async def get_link_to_fast_farm(message: Message, start=False) -> str:
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = await data.get_user(message.from_user.id)
    if user and not start:
        await print_fast_farm(message, send_message=True)
        return f'https://t.me/{(await bot.get_me()).username}'
    elif not user or start:
        return f'https://t.me/{(await bot.get_me()).username}?start=fast_farm'


async def get_user_relations(message, chat_id=None, num_of_group=0) -> str:
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts

    user_id = message.from_user.id

    if chat_id:
        last_message_chat_id = message.chat.id
        message.chat.id = chat_id
    user_bd = await data.get_chat_user(chat_id, user_id)
    user = (await bot.get_chat_member(chat_id, user_id)).user

    main_relation_user_id = await data.get_main_relation(chat_id, user.id)
    relations = await data.get_user_relations(message.chat.id, user.id)
    relations = sorted(relations,
                       key=lambda x: x['users'][0] != main_relation_user_id)
    relations = sorted(relations,
                       key=lambda x: x['users'][1] != main_relation_user_id)
    n = 10
    relations_groups = [relations[i:i + n] for i in range(0, len(relations), n)]

    relations = relations_groups[num_of_group]

    text_relations = [texts['my_relations'].format(await get_nickname(user))]
    for i, relation in enumerate(relations):
        partner_id = relation['users'][1] if relation['users'][0] == user.id else relation['users'][0]
        partner = (await bot.get_chat_member(message.chat.id, partner_id)).user
        time_registration = datetime.datetime.fromtimestamp(relation['time_registration'])
        seconds = (datetime.datetime.now() - time_registration).total_seconds()
        days = get_days(int(seconds))

        if user_bd['main_relation'] == partner.id:
            text_relations.append(
                f'{i + 1 + (num_of_group * n)}. ' + texts['my_main_relation'].format(await get_nickname(user),
                                                                                     await get_nickname(partner),
                                                                                     days,
                                                                                     relation['hp']))
        else:
            text_relations.append(
                f'{i + 1 + (num_of_group * n)}. ' + texts['my_relation'].format(await get_nickname(user),
                                                                                await get_nickname(partner),
                                                                                days,
                                                                                relation['hp']))
    if chat_id:
        message.chat.id = last_message_chat_id
    return '\n'.join(text_relations)


async def print_user_relations(message: Message, num_of_group, user_id=None, edit=False, send_message=False,
                               chat_id=None):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    if not chat_id:
        chat_id = message.chat.id

    user = message.from_user
    if user_id:
        user = (await bot.get_chat_member(chat_id, user_id)).user

    main_relation_user_id = await data.get_main_relation(chat_id, user.id)
    relations = await data.get_user_relations(chat_id, user.id)

    if not relations:
        if send_message:
            await bot.send_message(user.id, texts['my_relations__not'])
        else:
            await message.answer(texts['my_relations__not'])
        return

    relations = sorted(relations,
                       key=lambda x: x['users'][0] != main_relation_user_id or x['users'][1] != main_relation_user_id)
    n = 10
    relations_groups = [relations[i:i + n] for i in range(0, len(relations), n)]
    is_right, is_left = False, False
    if num_of_group < len(relations_groups) - 1:
        is_right = True
    if num_of_group > 0:
        is_left = True

    text = await get_user_relations(message, num_of_group=num_of_group, chat_id=chat_id)
    markup = inline.right_left(buttons, num_of_group,
                               chat_id,
                               user.id,
                               is_right, is_left)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        if send_message:
            await bot.send_message(user.id, text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)


async def print_fast_farm(message: Message, send_message=False):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = message.from_user
    main_channel = await data.get_main_channel()
    link = f'https://t.me/{(await bot.get_me()).username}'
    if main_channel:
        link = main_channel['link']

    if send_message:
        await bot.send_message(user.id, texts['fast_farm_channel'],
                               reply_markup=inline.fast_farm(buttons, link))
    else:
        await message.answer(texts['fast_farm_channel'], reply_markup=inline.fast_farm(buttons, link))


async def relations_user_callback(call: CallbackQuery):
    bot = call.bot
    data: Database = bot['db']
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    misc = bot['misc']
    texts = misc.texts

    chat_id = int(call.data.split(':')[1])
    user_id = int(call.data.split(':')[2])
    num_of_group = int(call.data.split(':')[-1])

    await print_user_relations(message, num_of_group, user_id, edit=True, chat_id=chat_id)
    await call.bot.answer_callback_query(call.id)


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


def get_days_hours(seconds: int) -> tuple:
    days = seconds // 86400
    hours = (seconds - days * 86400) // 3600
    return days, hours


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


def get_all_actions(misc) -> list:
    commands = []
    for r in misc.relations:
        for command in r['actions']:
            commands.append(command['command'])
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
    dp.register_callback_query_handler(relations_user_callback,
                                       text_contains='relations_user:')
    dp.register_callback_query_handler(list_actions_callback,
                                       text_contains='list_actions:')
    dp.register_message_handler(edit_description, state=EditDescription.description, content_types=ContentTypes.ANY,
                                is_group=True)
    dp.register_message_handler(chat, state="*", is_group=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
