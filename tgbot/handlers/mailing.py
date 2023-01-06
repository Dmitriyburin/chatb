import asyncio
import datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import MessageEntity, Message, ContentTypes, CallbackQuery
from aiogram.utils import exceptions
from tgbot.misc.states import GetMailing
from tgbot.keyboards import inline


async def get_mailing(message: Message, mailing):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    if mailing:
        await send_message_copy(bot, message.from_user.id, mailing['chat_id'],
                                mailing['message_id'],
                                mailing['markup'])
        if mailing['is_active']:
            await message.answer(texts['get_mailing__in_process'].format(mailing['sent'],
                                                                         mailing['not_sent']))
        else:
            await message.answer(get_mail_plan(mailing['date'], texts),
                                 reply_markup=inline.delete_mailing(buttons, mailing['message_id']))

        return


async def get_mailings(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    mailings = await data.get_mailings()
    if not mailings:
        await message.answer(texts['get_mailings_not'])

    for mailing in mailings:
        await get_mailing(message, mailing)


async def add_mailing_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    await GetMailing.mailing.set()
    await message.answer(texts['add_mailing__post'],
                         reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_mailing_post(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    post_message_id = message.message_id

    markup = None
    if message.reply_markup:
        markup = message.reply_markup.as_json()
    details = get_details(message)
    bot['mailing'] = {'post_message_id': post_message_id, 'markup': markup, 'details': details}
    await GetMailing.set_time.set()
    await message.answer(texts['add_mailing__time'], reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_mailing_time(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    bot['mailing']['date'] = None

    try:
        if message.text.lower() == 'сейчас' or message.text.lower() == 'now':
            await add_mailing(message, state)
            await state.finish()
            return

        date = datetime.datetime.strptime(message.text, "%H:%M %d.%m.%Y")
        if date < datetime.datetime.now():
            raise ValueError()

        bot['mailing']['date'] = date
        await add_mailing(message, state)

    except Exception as e:
        print(e)
        await message.answer(texts['add_mailing__time_uncorrected'],
                             reply_markup=inline.cancel(buttons, 'cancel:mailing'))
        return

    await state.finish()


async def add_mailing(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    post_message_id, markup, details = bot['mailing']['post_message_id'], \
                                       bot['mailing']['markup'], bot['mailing']['details']
    date = bot['mailing']['date']
    await data.add_mailing(message.chat.id, post_message_id, markup, details, date)

    mailing = await data.get_mailing(post_message_id)
    if date:
        await get_mailing(message, mailing)
    else:
        await data.set_active_mailing(mailing['message_id'], True)
        await message.answer(texts['mailing__start'])


def get_mail_plan(date, texts) -> str:
    days = (date - datetime.datetime.now()).days
    seconds = (date - datetime.datetime.now()).seconds

    hours = seconds // 3600
    minutes = (seconds - (hours * 3600)) // 60
    if (hours + days * 24) < 0:
        return texts['mailing__queue']
    return texts['get_mailing__plan'].format(hours + days * 24, minutes)


async def send_message_copy(bot, user_id, from_chat_id, message_id, markup):
    try:
        await bot.copy_message(user_id, from_chat_id, message_id, reply_markup=markup)
        return True
    except Exception as e:
        return False


async def send_second_method(bot, user_id, details, markup):
    entities = []
    for entity in details['entities']:
        entity = eval(entity)
        url = None if not 'url' in entity.keys() else entity['url']
        entities.append(MessageEntity(type=entity['type'], offset=entity['offset'], length=entity['length'], url=url))

    try:
        if details['type'] == 'text':
            await bot.send_message(user_id, details['text'], entities=entities, reply_markup=markup,
                                   disable_web_page_preview=True)
        elif details['type'] == 'photo':
            await bot.send_photo(user_id, photo=details['file_id'], caption=details['caption'],
                                 caption_entities=entities, reply_markup=markup)
        elif details['type'] == 'video':
            await bot.send_video(user_id, video=details['file_id'], caption=details['caption'],
                                 caption_entities=entities, reply_markup=markup)
        elif details['type'] == 'gif':
            await bot.send_animation(user_id, animation=details['file_id'], caption=details['caption'],
                                     caption_entities=entities, reply_markup=markup)
        elif details['type'] == 'voice':
            await bot.send_voice(user_id, voice=details['file_id'], caption=details['caption'],
                                 caption_entities=entities, reply_markup=markup)
        return True
    except exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return False
    except Exception as e:
        return False


async def mailing_controller(bot, delay):
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    admins = bot['config'].tg_bot.admin_ids
    while True:
        await asyncio.sleep(delay)
        mailings = await data.get_mailings()

        if not mailings:
            continue
        else:
            await asyncio.sleep(10)

        for mailing in mailings:
            if mailing['is_active']:
                break
        else:
            for mailing in mailings:
                if mailing['date']:
                    if datetime.datetime.now() >= mailing['date']:
                        break
            else:
                continue

            await data.set_active_mailing(mailing['message_id'], True)

        user_ids = await data.get_mailing_users()
        if user_ids:
            sent = 0
            not_sent = 0
            tasks = [send_message_copy(bot, user_id, mailing['chat_id'], mailing['message_id'],
                                       mailing['markup'])
                     for user_id in user_ids]
            if mailing['details']['type']:
                user_ids = await data.get_mailing_users()
                for user_id in user_ids:
                    tasks.append(send_second_method(bot, user_id, mailing['details'], mailing['markup']))

            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    sent += 1
                else:
                    not_sent += 1
            await data.edit_mailing_progress(mailing['message_id'], sent, not_sent)
        else:

            for admin in admins:
                await bot.send_message(admin,
                                       texts['mailing_finished'].format(mailing['sent'] + mailing['not_sent'],
                                                                        mailing['users_count'], mailing['sent'],
                                                                        mailing['not_sent']))
            await data.del_mailing(mailing['message_id'])


def get_details(message: Message):
    details = {'type': None}

    if message.text:
        details['type'] = 'text'
        details['text'] = message.text
        details['entities'] = [i.as_json() for i in message.entities]
    elif message.photo:
        details['type'] = 'photo'
        details['file_id'] = message.photo[-1].file_id
        details['caption'] = message.caption
        details['entities'] = [i.as_json() for i in message.caption_entities]
    elif message.video:
        details['type'] = 'video'
        details['file_id'] = message.video.file_id
        details['caption'] = message.caption
        details['entities'] = [i.as_json() for i in message.caption_entities]
    elif message.animation:
        details['type'] = 'gif'
        details['file_id'] = message.animation.file_id
        details['caption'] = message.caption
        details['entities'] = [i.as_json() for i in message.caption_entities]
    return details


async def cancel(call: CallbackQuery, state: FSMContext):
    message = call.message
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    detail = call.data.split(':')[1]
    message.from_user.id = call['from']['id']

    if detail == 'mailing':
        await state.finish()
        await message.delete()
    elif detail.split('-')[0] == 'mailing2':
        message_id = int(detail.split('-')[1])
        await data.del_mailing(message_id)
        await message.answer(texts['del_mailing__success'])
        await message.edit_reply_markup(reply_markup=None)
    await bot.answer_callback_query(call.id)


def register_mailing(dp: Dispatcher):
    dp.register_message_handler(get_mailing, commands=["mailing"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(get_mailings, commands=["mailings"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(add_mailing_start, commands=["add_mailing"], state="*", is_admin=True)
    dp.register_message_handler(add_mailing_post, state=GetMailing.mailing, content_types=ContentTypes.ANY,
                                is_private=True)
    dp.register_message_handler(add_mailing_time, state=GetMailing.set_time, content_types=ContentTypes.ANY,
                                is_private=True)

    dp.register_callback_query_handler(cancel, state="*", text_contains='cancel:')


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
