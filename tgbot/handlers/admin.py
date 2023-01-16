import logging
import requests
import itertools
import datetime
import os

from aiogram import Dispatcher

from aiogram.types import Message, CallbackQuery, Update
from aiogram.dispatcher import FSMContext
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils import exceptions
from tgbot.misc.states import AddChannel, DeleteChannel, AddRef, DeleteRef, BanUser
from tgbot.misc.states import StatsRef, RefsMonth, UnbanUser, ExtraditionMoney
from tgbot.misc.functions import generate_start_ref, get_start_url_by_ref, parse_ref_from_link
from tgbot.handlers.mailing import mailing_choice
from tgbot.keyboards import inline


async def admin_main(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    await message.answer(texts['admin'])


async def admin_main_2(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons
    await message.answer('Админ панель', reply_markup=inline.admin(buttons))


async def add_channel_start(message: Message, state: FSMContext, is_main=False):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['add_channel__id'], reply_markup=inline.cancel_main(buttons))
    await AddChannel.channel.set()
    await state.update_data(is_main=is_main)


async def add_channel(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    try:
        bot['channel_id'] = int(message.text)
        await message.answer(texts['add_channel__link'], reply_markup=inline.cancel_main(buttons))
        await AddChannel.link.set()
    except Exception as e:
        await message.answer(texts['add_channel__id_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return


async def add_link_channel(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['add_channel__success'])
    is_main = (await state.get_data())['is_main']
    await data.add_channel(bot['channel_id'], message.text, is_main)

    await state.finish()


async def add_main_channel_start(message: Message, state: FSMContext):
    await add_channel_start(message, state, is_main=True)


async def get_channels(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    channels = []
    for index, item in enumerate(await data.get_channels()):
        if item.get('is_main'):
            channels.append(texts['get_channels__one_main'].format(index + 1, item['link'], item['link']))
        else:
            channels.append(texts['get_channels__one'].format(index + 1, item['link'], item['link']))

    if channels:
        await message.answer('\n'.join(channels), disable_web_page_preview=True)
    else:
        await message.answer(texts['get_channels__not'])


async def del_channel_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['del_channel__link'], reply_markup=inline.cancel_main(buttons))
    await DeleteChannel.channel.set()


async def del_channel(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    if await data.get_channel(message.text):
        await data.del_channel(message.text)
        await message.answer(texts['del_channel__success'])
        await state.finish()
    else:
        await message.answer(texts['del_channel__not_found'], reply_markup=inline.cancel_main(buttons))
        return


async def users_file(message: Message):
    bot = message.bot
    data: Database = bot['db']

    fname = 'users.txt'
    with open(fname, 'w') as file:
        for user in await data.get_users():
            file.write(str(user['user_id']) + '\n')
        async for chat in (await data.get_chats()):
            file.write(str(chat['chat_id']) + '\n')

    await message.answer_document(open(fname, 'rb'))
    os.remove(fname)


async def stats(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    stats_all = await data.get_stats_real()
    all_users = stats_all['all_users']
    all_chats = stats_all['all_chats']
    all_chats_users = stats_all['all_chats_users']
    dead_groups = stats_all['dead_groups']

    users_live, users_die, groups_live = 0, 0, all_chats - dead_groups
    male, female = '0%', '0%'
    access_key = misc.botstat_key
    botstat = requests.get(f'https://api.botstat.io/get/{(await bot.get_me()).username}/{access_key}').json()
    if botstat['ok']:
        logging.info(botstat)
        users_die = botstat['result']['users_die']
        users_live = botstat['result']['users_live']
        groups_live = botstat['result']['groups_live']
        male = botstat['result'].get('male', male)
        female = botstat['result'].get('female', female)
    await message.answer(
        texts['stats'].format(all_users, users_live, users_die, male, female, all_chats, groups_live, all_chats_users))


async def add_ref_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['add_ref__date'], reply_markup=inline.cancel_main(buttons))
    await AddRef.date.set()


async def add_ref_date(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    try:
        date = datetime.datetime.strptime(message.text, "%d.%m.%Y")

        await message.answer(texts['add_ref__price'], reply_markup=inline.cancel_main(buttons))
        await AddRef.price.set()
        await state.update_data(date=date.isoformat())
    except Exception as e:
        logging.error(e)
        await message.answer(texts['add_ref__date_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return


async def add_ref(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    price = message.text.replace(' ', '')
    if not price.isdigit():
        await message.answer(texts['add_ref__price_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return

    await state.update_data(price=price)
    await message.answer(texts['add_ref__contact'], reply_markup=inline.cancel_main(buttons))
    await AddRef.contact.set()


async def add_ref_contact(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    contact = message.text

    ref = await generate_start_ref(data)
    price = (await state.get_data())['price']
    date = datetime.datetime.fromisoformat((await state.get_data())['date'])

    await message.answer(texts['add_ref__success'].format(await get_start_url_by_ref(bot, ref)))
    await data.add_ref(ref, int(price), contact, date)
    await state.finish()


async def get_refs(message: Message, state: FSMContext, month=-1, edit=False):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    channels_text = []
    channels = list(sorted((await data.get_refs()), key=lambda x: x['date']))
    if not channels:
        await message.answer(texts['get_refs__not_found'])
        return

    channels_per_month = [list(v) for k, v in itertools.groupby(channels, lambda e: (e['date'].month, e['date'].year))]
    if month == -1:
        month = len(channels_per_month) - 1
    for index, item in enumerate(channels_per_month[month]):
        link = await get_start_url_by_ref(bot, item['ref'])
        channels_text.append(texts['get_refs__one'].format(index + 1, link, item['date'].date(),
                                                           item['price'], item['contact']))
    n = 10
    answer = [channels_text[i:i + n] for i in range(0, len(channels_text), n)]
    count = 0
    messages_ids = []
    for text in answer:
        count += 1

        markup = None
        if count == len(answer):
            is_next = True if (month + 1) <= (len(channels_per_month) - 1) else None
            is_last = True if month != 0 else None
            await RefsMonth.month_callback.set()
            await state.update_data(messages_ids=messages_ids)
            markup = inline.next_or_last(month, is_next, is_last)

        if count == 1 and edit:
            message = await message.edit_text('\n'.join(text), reply_markup=markup)
        else:
            if not message.get_command():
                messages_ids.append(message.message_id)
            message = await message.answer('\n'.join(text), reply_markup=markup)


async def month_callback(call: CallbackQuery, state: FSMContext):
    month = call.data.split(':')[1]

    delete_messages_ids = (await state.get_data())['messages_ids']
    for message_id in delete_messages_ids:
        await call.bot.delete_message(call['from']['id'], int(message_id))
    await state.finish()
    await get_refs(call.message, state, int(month), edit=True)
    await call.bot.answer_callback_query(call.id)


async def ref_stats_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['get_stats_ref__link'], reply_markup=inline.cancel_main(buttons))
    await StatsRef.ref.set()


async def ref_stats(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    ref = await data.get_ref(await parse_ref_from_link(message.text))
    if ref:
        ref_stat = await data.ref_stats(ref['ref'])
        users = ref_stat['all_users']
        users_channel = len(ref['users_channel'])

        if users != 0:
            price_user = round(ref['price'] / users, 3)
            subs_pr = round(users_channel / users * 100, 3)
        else:
            price_user, subs_pr = 0, 0

        await message.answer(texts['link_stats'].format(users, users_channel, subs_pr, ref['price'],
                                                        price_user))
    else:
        await message.answer(texts['get_stats_ref__not_found'], reply_markup=inline.cancel_main(buttons))
        return
    await state.finish()


async def del_ref_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['del_ref__link'], reply_markup=inline.cancel_main(buttons))
    await DeleteRef.ref.set()


async def del_ref(message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    if await data.get_ref(message.text):
        await data.delete_ref(message.text)
        await message.answer(texts['del_ref__success'])
        await state.finish()
    else:
        await message.answer(texts['del_ref__not_found'], reply_markup=inline.cancel_main(buttons))
        return


async def ban_user_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['ban_user__id'], reply_markup=inline.cancel_main(buttons))
    await BanUser.user_id.set()


async def ban_user(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    user_id = message.text
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    if not user_id.isdigit():
        await message.answer(texts['ban_user__id_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return

    await data.ban_user(int(user_id))
    await message.answer(texts['ban_user__success'])
    await state.finish()


async def sent_ban_to_channel(bot, message: Message, banned_user_id, is_unban=False):
    sent_message = f'<code>{message.from_user.id}</code> @{message.from_user.username} забанил <code>{banned_user_id}</code>'
    if is_unban:
        sent_message = f'<code>{message.from_user.id}</code> @{message.from_user.username} разбанил <code>{banned_user_id}</code>'

    await bot.send_message(bot['config'].channel_id_to_send_ban, sent_message)


async def unban_user_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['unban_user__id'], reply_markup=inline.cancel_main(buttons))
    await UnbanUser.user_id.set()


async def unban_user(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    user_id = message.text
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    if not user_id.isdigit():
        await message.answer(texts['unban_user__id_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return

    await data.unban_user(int(user_id))
    await message.answer(texts['unban_user__success'])
    await sent_ban_to_channel(bot, message, user_id, is_unban=True)
    await state.finish()


async def extradition_money_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['extradition_money__user_id'], reply_markup=inline.cancel_main(buttons))
    await ExtraditionMoney.user_id.set()


async def extradition_money_user_id(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    user_id = message.text
    if not user_id.isdigit():
        await message.answer(texts['extradition_money__user_id_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return

    await state.update_data(user_id=int(user_id))
    await message.answer(texts['extradition_money__count'], reply_markup=inline.cancel_main(buttons))
    await ExtraditionMoney.count.set()


async def extradition_money(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    count = message.text
    if not count.isdigit():
        await message.answer(texts['extradition_money__count_uncorrected'], reply_markup=inline.cancel_main(buttons))
        return

    state_data = await state.get_data()
    await data.increase_coins(state_data['user_id'], int(count))
    await message.answer(texts['extradition_money__success'])
    await state.finish()


async def channels_choice(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['channels__choice'], reply_markup=inline.channels_choice(buttons))
    await message.delete()


async def channels_choice_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[1]
    logging.info(action)
    if action == 'add':
        await add_channel_start(message, state)
    elif action == 'add_main':
        await add_channel_start(message, state, is_main=True)
    elif action == 'delete':
        await del_channel_start(message)
    elif action == 'print':
        await get_channels(message)
    await call.bot.answer_callback_query(call.id)


async def refs_choice(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['refs__choice'], reply_markup=inline.refs_choice(buttons))
    await message.delete()


async def refs_choice_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[1]
    logging.info(action)
    if action == 'add':
        await add_ref_start(message)
    elif action == 'stats':
        await ref_stats_start(message)
    elif action == 'delete':
        await del_ref_start(message, state)
    elif action == 'print':
        await get_refs(message, state)
        await message.delete()
    await call.bot.answer_callback_query(call.id)


async def extradition_choice(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['extradition__choice'], reply_markup=inline.extradition_choice(buttons))
    await message.delete()


async def extradition_choice_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[1]
    logging.info(action)
    if action == 'money':
        await extradition_money_start(message, state)
    await call.bot.answer_callback_query(call.id)


async def admin_callback(call: CallbackQuery):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[1]
    if action == 'mailing':
        await mailing_choice(message)
    elif action == 'channels':
        await channels_choice(message)
    elif action == 'stats':
        await stats(message)
    elif action == 'refs':
        await refs_choice(message)
    elif action == 'users':
        await users_file(message)
    elif action == 'extradition':
        await extradition_choice(message)
    await call.bot.answer_callback_query(call.id)


async def finish_state(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Состояние удалено')


async def bot_blocked(update: Update, exception: exceptions.BotBlocked):
    bot = update.bot
    data: Database = bot['db']
    logging.info('бан')
    logging.info(update)
    # await data.add_dead_user(update)


async def get_id(message: Message):
    await message.answer(f'Твой id: <code>{message.from_user.id}</code>')


def register_admin(dp: Dispatcher):
    dp.register_errors_handler(bot_blocked, exception=exceptions.BotBlocked)

    dp.register_message_handler(admin_main_2, commands=["admin"], state="*", is_admin=True, is_private=True)
    dp.register_callback_query_handler(admin_callback, state="*",
                                       text_contains='admin:',
                                       is_admin=True, is_private=True)
    dp.register_callback_query_handler(channels_choice_callback, state="*",
                                       text_contains='channels_choice:',
                                       is_admin=True, is_private=True)
    dp.register_callback_query_handler(refs_choice_callback, state="*",
                                       text_contains='refs_choice:',
                                       is_admin=True, is_private=True)
    dp.register_callback_query_handler(extradition_choice_callback, state="*",
                                       text_contains='extradition_choice:',
                                       is_admin=True, is_private=True)
    dp.register_message_handler(admin_main, commands=["admin2"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(add_channel_start, commands=["add_sub"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(add_main_channel_start, commands=["add_main_sub"], state="*", is_admin=True,
                                is_private=True)
    dp.register_message_handler(add_channel, state=AddChannel.channel, is_admin=True, is_private=True)
    dp.register_message_handler(add_link_channel, state=AddChannel.link, is_admin=True, is_private=True)

    dp.register_message_handler(del_channel_start, commands=["del_sub"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(del_channel, state=DeleteChannel.channel, is_admin=True, is_private=True)

    dp.register_message_handler(get_channels, commands=["channels"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(users_file, commands=["users"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(stats, commands=["stats"], state="*", is_admin=True, is_private=True)

    dp.register_message_handler(add_ref_start, commands=["add_ref"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(add_ref_date, state=AddRef.date, is_admin=True, is_private=True)
    dp.register_message_handler(add_ref_contact, state=AddRef.contact, is_admin=True, is_private=True)
    dp.register_message_handler(add_ref, state=AddRef.price, is_admin=True, is_private=True)
    dp.register_message_handler(del_ref_start, commands=["del_ref"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(del_ref, state=DeleteRef.ref, is_admin=True, is_private=True)
    dp.register_message_handler(get_refs, commands=["refs"], state="*", is_admin=True, is_private=True)
    dp.register_callback_query_handler(month_callback, state=RefsMonth.month_callback,
                                       text_contains='month:',
                                       is_admin=True, is_private=True)
    dp.register_message_handler(ref_stats_start, commands=["ref_stats"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(ref_stats, state=StatsRef.ref, is_admin=True, is_private=True)

    # dp.register_message_handler(ban_user_start, commands=["ban"], state="*", is_admin=True, is_private=True)
    # dp.register_message_handler(ban_user, state=BanUser.user_id, is_admin=True, is_private=True)

    # dp.register_message_handler(unban_user_start, commands=["unban"], state="*", is_admin=True, is_private=True)
    # dp.register_message_handler(unban_user, state=UnbanUser.user_id, is_admin=True, is_private=True)

    dp.register_message_handler(finish_state, commands=["finish_state"], is_admin=True)
    dp.register_message_handler(get_id, commands=["id"], is_admin=True)
    dp.register_message_handler(extradition_money_user_id, state=ExtraditionMoney.user_id, is_admin=True,
                                is_private=True)
    dp.register_message_handler(extradition_money, state=ExtraditionMoney.count, is_admin=True, is_private=True)


if __name__ == '__main__':
    from ..misc.functions import generate_start_ref
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
