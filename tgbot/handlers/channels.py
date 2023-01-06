import logging

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

        else:
            await call.answer(texts['sponsor__not'])

    await bot.answer_callback_query(call.id)


def register_channels(dp: Dispatcher):
    dp.register_callback_query_handler(check_sub_call, text_contains='check_sub_call', state='*', is_private=True)
    dp.register_message_handler(required_channel, state=RequiredChannel.required_channel, is_private=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
