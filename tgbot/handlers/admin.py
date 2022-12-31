import logging
import random
import itertools
import datetime
import os

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.utils.deep_linking import get_start_link
from tgbot.misc.states import AddChannel, DeleteChannel, AddRef, DeleteRef, BanUser
from tgbot.misc.states import StatsRef, RefsMonth, UnbanUser
from tgbot.misc.functions import generate_start_ref, get_start_url_by_ref, parse_ref_from_link
from tgbot.keyboards import inline


async def admin_main(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    await message.answer(texts['admin'])


async def add_channel_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    await message.answer(texts['add_channel__id'])
    await AddChannel.channel.set()


async def add_channel(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    try:
        bot['channel_id'] = int(message.text)
        await message.answer(texts['add_channel__link'])
        await AddChannel.link.set()
    except Exception as e:
        await message.answer(texts['add_channel__id_uncorrected'])
        await state.finish()


async def add_link_channel(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['add_channel__success'])
    await data.add_channel(bot['channel_id'], message.text)

    await state.finish()


async def get_channels(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    channels = []
    for index, item in enumerate(await data.get_channels()):
        channels.append(texts['get_channels__one'].format(index + 1, item['link'], item['link']))
    if channels:
        await message.answer('\n'.join(channels), disable_web_page_preview=True)
    else:
        await message.answer(texts['get_channels__not'])


async def del_channel_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['del_channel__link'])
    await DeleteChannel.channel.set()


async def del_channel(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    if await data.get_channel(message.text):
        await data.del_channel(message.text)
        await message.answer(texts['del_channel__success'])
        await state.finish()
    else:
        await message.answer(texts['del_channel__not_found'])
        await state.finish()


async def users_file(message: Message):
    bot = message.bot
    data: Database = bot['db']

    fname = 'users.txt'
    with open(fname, 'w') as file:
        async for user in await data.get_users():
            file.write(str(user['user_id']) + '\n')

    await message.answer_document(open(fname, 'rb'))
    os.remove(fname)


async def stats(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    stats_all = await data.get_stats()
    price = stats_all['price']
    users_count = stats_all['users_count']
    await message.answer(texts['stats'].format(users_count, price))


async def add_ref_start(message: Message):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['add_ref__date'])
    await AddRef.date.set()


async def add_ref_date(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    try:
        date = datetime.datetime.strptime(message.text, "%d.%m.%Y")

        await message.answer(texts['add_ref__price'])
        await AddRef.price.set()
        await state.update_data(date=date.isoformat())
    except Exception as e:
        logging.error(e)
        await message.answer(texts['add_ref__date_uncorrected'])
        await state.finish()


async def add_ref(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    price = message.text.replace(' ', '')
    if not price.isdigit():
        await message.answer(texts['add_ref__price_uncorrected'])
        await state.finish()
        return
    await state.update_data(price=price)
    await message.answer(texts['add_ref__contact'])
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

        if item['transitions'] != 0:
            price_transitions = round(item['price'] / item['transitions'], 3)
        else:
            price_transitions = 0

        link = await get_start_url_by_ref(bot, item['ref'])
        channels_text.append(texts['get_refs__one'].format(index + 1, link, item['date'].date(),
                                                           item['price'], item['contact'], price_transitions))
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

    await message.answer(texts['get_stats_ref__link'])
    await StatsRef.ref.set()


async def ref_stats(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    ref = await data.get_ref(await parse_ref_from_link(message.text))
    if ref:
        ref_stat = await data.ref_stats(ref['ref'])
        users = ref_stat['all_users']

        if ref['transitions'] != 0:
            price_transitions = round(ref['price'] / ref['transitions'], 3)
        else:
            price_transitions = 0

        if users != 0:
            price_user = round(ref['price'] / users, 3)
        else:
            price_user = 0

        await message.answer(texts['link_stats'].format(users, ref['transitions'], ref['price'],
                                                        price_transitions, price_user,
                                                        ref['donaters'],
                                                        ref['all_price']))
    else:
        await message.answer(texts['get_stats_ref__not_found'])
    await state.finish()


async def del_ref_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['del_ref__link'])
    await DeleteRef.ref.set()


async def del_ref(message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    if await data.get_ref(message.text):
        await data.delete_ref(message.text)
        await message.answer(texts['del_ref__success'])
        await state.finish()
    else:
        await message.answer(texts['del_ref__not_found'])
        await state.finish()


async def ban_user_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    await message.answer(texts['ban_user__id'])
    await BanUser.user_id.set()


async def ban_user(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    user_id = message.text
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    if not user_id.isdigit():
        await message.answer(texts['ban_user__id_uncorrected'])
        await state.finish()
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

    await message.answer(texts['unban_user__id'])
    await UnbanUser.user_id.set()


async def unban_user(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    user_id = message.text
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    if not user_id.isdigit():
        await message.answer(texts['unban_user__id_uncorrected'])
        await state.finish()
        return

    await data.unban_user(int(user_id))
    await message.answer(texts['unban_user__success'])
    await sent_ban_to_channel(bot, message, user_id, is_unban=True)
    await state.finish()


def register_admin(dp: Dispatcher):
    dp.register_message_handler(admin_main, commands=["admin"], state="*", is_admin=True)
    dp.register_message_handler(add_channel_start, commands=["add_sub"], state="*", is_admin=True)
    dp.register_message_handler(add_channel, state=AddChannel.channel, is_admin=True)
    dp.register_message_handler(add_link_channel, state=AddChannel.link, is_admin=True)

    dp.register_message_handler(del_channel_start, commands=["del_sub"], state="*", is_admin=True)
    dp.register_message_handler(del_channel, state=DeleteChannel.channel, is_admin=True)

    dp.register_message_handler(get_channels, commands=["channels"], state="*", is_admin=True)
    dp.register_message_handler(users_file, commands=["users"], state="*", is_admin=True)
    dp.register_message_handler(stats, commands=["stats"], state="*", is_admin=True)

    dp.register_message_handler(add_ref_start, commands=["add_ref"], state="*", is_admin=True)
    dp.register_message_handler(add_ref_date, state=AddRef.date, is_admin=True)
    dp.register_message_handler(add_ref_contact, state=AddRef.contact, is_admin=True)
    dp.register_message_handler(add_ref, state=AddRef.price, is_admin=True)
    dp.register_message_handler(del_ref_start, commands=["del_ref"], state="*", is_admin=True)
    dp.register_message_handler(del_ref, state=DeleteRef.ref, is_admin=True)
    dp.register_message_handler(get_refs, commands=["refs"], state="*", is_admin=True)
    dp.register_callback_query_handler(month_callback, state=RefsMonth.month_callback,
                                       text_contains='month:',
                                       is_admin=True)
    dp.register_message_handler(ref_stats_start, commands=["ref_stats"], state="*", is_admin=True)
    dp.register_message_handler(ref_stats, state=StatsRef.ref, is_admin=True)

    dp.register_message_handler(ban_user_start, commands=["ban"], state="*", is_admin=True)
    dp.register_message_handler(ban_user, state=BanUser.user_id, is_admin=True)

    dp.register_message_handler(unban_user_start, commands=["unban"], state="*", is_admin=True)
    dp.register_message_handler(unban_user, state=UnbanUser.user_id, is_admin=True)


if __name__ == '__main__':
    from ..misc.functions import generate_start_ref
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
