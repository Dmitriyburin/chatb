import logging
import asyncio

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import BadRequest, Unauthorized
from tgbot.keyboards import inline
from tgbot.misc.states import RequiredChannel


async def required_channel(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    channels = await check_sub(message)
    await message.answer(texts['sponsor'],
                         reply_markup=inline.required_sub(buttons, channels))


async def check_sub(message):
    bot = message.bot
    data: Database = bot['db']

    channels = [item for index, item in enumerate(await data.get_channels())]
    channels_links = []
    for channel in channels:
        chat_id = channel['channel_id']
        if channel.get('is_main'):
            continue
        try:
            user_channel = await bot.get_chat_member(chat_id=f'{chat_id}', user_id=message.from_user.id)
            if user_channel.status not in ['member', 'administrator', 'creator']:
                channels_links.append(channel['link'])

        except BadRequest as e:
            logging.error(e)
            continue

        except Unauthorized as e:
            logging.error(e)
            continue

        except Exception as e:
            logging.error(e)
            continue

    user = await data.get_user(message.from_user.id)
    if await data.get_is_ref_commercial(user['ref']):
        await data.increment_subs_ref_commercial(user['ref'], len(channels))
    return channels_links


async def check_sub_call(call: CallbackQuery, state: FSMContext):
    message = call.message
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    message.from_user.id = call['from']['id']

    detail = call.data.split(':')[1]
    if detail == 'channel':
        channels = await check_sub(message)
        if not channels:
            await message.delete()
            await message.answer(texts['sponsor__success'])
            await state.finish()
            user_db = await data.get_user(message.from_user.id)
            if user_db['ref']:
                await data.add_user_channel_to_ref_if_not_exists(user_db['ref'], user_db['user_id'])

        else:
            await call.answer(texts['sponsor__not'])
    elif detail == 'main_channel':
        main_channel = await data.get_main_channel()
        user_channel = await bot.get_chat_member(chat_id=main_channel['channel_id'], user_id=message.from_user.id)
        if user_channel.status not in ['member', 'administrator', 'creator']:
            await message.answer(texts['main_channel__not_subscribe'])
        else:
            await data.set_hours_for_next_time(message.from_user.id, 3)
            await message.answer(texts['main_channel__success_subscribe'])
            await message.delete()

    await bot.answer_callback_query(call.id)


async def main_channel_controller(bot, delay):
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts

    while True:
        await asyncio.sleep(delay)

        users_chats = await data.get_3_hours_farm_users_chats()
        main_channel = await data.get_main_channel()
        if not main_channel:
            continue

        async for user in users_chats:
            user_channel = await bot.get_chat_member(chat_id=main_channel['channel_id'],
                                                     user_id=user['user_id'])
            if user_channel.status not in ['member', 'administrator', 'creator']:
                await data.set_hours_for_next_time(user['user_id'], 4)
                await bot.send_message(user['user_id'], texts['main_channel__unsubscribe'])


def register_channels(dp: Dispatcher):
    dp.register_callback_query_handler(check_sub_call, text_contains='check_sub_call', state='*', is_private=True)
    dp.register_message_handler(required_channel, state=RequiredChannel.required_channel, is_private=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
