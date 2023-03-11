import asyncio
import datetime
import json
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore

from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.types import MessageEntity, Message, ContentTypes, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils import exceptions
from tgbot.misc.states import GetMailing, AddMailingSingle
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
    await state.update_data(is_group=False)
    await message.answer(texts['add_mailing__post'],
                         reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_group_mailing_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    await GetMailing.mailing.set()
    await state.update_data(is_group=True)
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
    await state.update_data(
        mailing=json.dumps({'post_message_id': post_message_id, 'markup': markup, 'details': details}))
    await GetMailing.set_time.set()
    await message.answer(texts['add_mailing__time'], reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_mailing_time(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']
    logging.info(message.text)
    try:
        if message.text.lower() == 'сейчас' or message.text.lower() == 'now':
            await add_mailing(message, state)
            return

        date = datetime.datetime.strptime(message.text, "%H:%M %d.%m.%Y")
        logging.info(date)
        if date < datetime.datetime.now():
            raise ValueError()

        await state.update_data(date=date.timestamp())
        await add_mailing(message, state)

    except Exception as e:
        logging.info(e)
        await message.answer(texts['add_mailing__time_uncorrected'],
                             reply_markup=inline.cancel(buttons, 'cancel:mailing'))
        return


async def add_mailing(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']

    state_date = await state.get_data()
    logging.info(state_date)
    mailing = json.loads(state_date['mailing'])
    post_message_id, markup, details, is_group = mailing['post_message_id'], mailing['markup'], \
                                                 mailing['details'], state_date['is_group']
    date = state_date.get('date')
    if date:
        date = datetime.datetime.fromtimestamp(state_date.get('date'))

    await data.add_mailing(message.chat.id, post_message_id, markup, details, date, is_group=is_group)
    mailing = await data.get_mailing(post_message_id)
    if date:
        await get_mailing(message, mailing)
    else:
        await data.set_active_mailing(mailing['message_id'], True, is_group=is_group)
        await message.answer(texts['mailing__start'])
    await state.finish()


async def add_single_group_mailing_start(message: Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    await AddMailingSingle.post_id.set()
    await message.answer(texts['add_mailing_single__post'],
                         reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_single_group_mailing_post(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    post_message_id = message.message_id
    markup = None
    if message.reply_markup:
        markup = message.reply_markup.as_json()

    await state.update_data(post_id=post_message_id, markup=markup)
    await AddMailingSingle.group_id.set()
    await message.answer(texts['add_mailing__group_id'], reply_markup=inline.cancel(buttons, 'cancel:mailing'))


async def add_single_group_mailing_id(message: Message, state: FSMContext):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    group_id = int(message.text)
    post_id = int((await state.get_data())['post_id'])
    markup = (await state.get_data())['markup']
    not_loads_mark = markup
    if markup:
        markup = InlineKeyboardMarkup.to_object(json.loads(markup))

    bot = message.bot
    message_id = (await bot.copy_message(group_id, message.from_user.id, post_id,
                                         reply_markup=markup)).message_id
    scheduler = bot['scheduler']
    job = scheduler.add_job(mailing_to_group, 'interval', minutes=10, args=(None, None, None, None, None, None))
    job.modify(args=(bot, group_id, not_loads_mark, scheduler, job.id, message_id))
    await data.add_job(group_id, message_id, job.id, not_loads_mark)

    await state.finish()
    await message.answer(texts['mailing__start'])


async def print_single_mailings(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    buttons = misc.buttons
    texts = misc.texts['admin_texts']

    jobs = await data.get_jobs()
    async for job in jobs:
        await message.answer(f"👇 ID Чата: <code>{job['group_id']}</code>")
        try:
            await bot.copy_message(message.from_user.id, job['group_id'], job['message_id'],
                                   reply_markup=inline.delete(f"delete_single_group_mailing:{job['group_id']}"))
        except Exception:
            await message.answer(texts['mailing_single__not_found'],
                                 reply_markup=inline.delete(f"delete_single_group_mailing:{job['group_id']}"))
        await message.answer('-' * 10)


async def delete_single_group_mailing_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    data: Database = bot['db']
    misc = bot['misc']
    buttons = misc.buttons
    scheduler: AsyncIOScheduler = bot['scheduler']
    texts = misc.texts['admin_texts']
    group_id = int(call.data.split(':')[2])
    logging.info(group_id)
    job = await data.get_job(group_id)
    scheduler.remove_job(job['job_id'])
    await data.delete_job(group_id)
    await call.message.delete()


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

            await data.set_active_mailing(mailing['message_id'], True, is_group=mailing.get('is_group'))

        if not mailing.get('is_group'):
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
        else:
            groups_ids = await data.get_mailing_groups()
            logging.info(groups_ids)
            if groups_ids:
                sent = 0
                not_sent = 0
                tasks = [send_message_copy(bot, group_id, mailing['chat_id'], mailing['message_id'],
                                           mailing['markup'])
                         for group_id in groups_ids]

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


async def mailing_to_group(bot: Bot, group_id, markup, scheduler: AsyncIOScheduler, job_id,
                           last_message_id=None):
    not_loads_markup = markup
    if markup:
        markup = InlineKeyboardMarkup.to_object(
            json.loads(markup))
    data: Database = bot['db']
    current_message_id = (await bot.copy_message(group_id, group_id, last_message_id,
                                                 reply_markup=markup)).message_id
    logging.info(not_loads_markup)
    scheduler.modify_job(job_id, args=(bot, group_id, not_loads_markup, scheduler, job_id, current_message_id))
    await data.update_job(group_id, current_message_id, job_id)
    if last_message_id:
        await bot.delete_message(group_id, last_message_id)


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
    elif detail == 'main':
        await state.finish()
        await message.delete()
    elif detail.split('-')[0] == 'mailing2':
        message_id = int(detail.split('-')[1])
        await data.del_mailing(message_id)
        await message.answer(texts['del_mailing__success'])
        await message.edit_reply_markup(reply_markup=None)
    await bot.answer_callback_query(call.id)


async def mailing_choice(message: Message):
    bot = message.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts['admin_texts']
    buttons = misc.buttons

    await message.answer(texts['mailing_choice'], reply_markup=inline.mailing_choice(buttons))
    await message.delete()


async def mailing_choice_callback(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    action = call.data.split(':')[1]
    logging.info(action)
    if action == 'print':
        await get_mailings(message, state)
    elif action == 'add':
        await add_mailing_start(message, state)
    elif action == 'users':
        await add_mailing_start(message, state)
    elif action == 'groups':
        await add_group_mailing_start(message, state)
    elif action == 'add_single':
        await add_single_group_mailing_start(message, state)
    elif action == 'print_singles':
        await print_single_mailings(message)
    await call.bot.answer_callback_query(call.id)


def register_mailing(dp: Dispatcher):
    dp.register_message_handler(get_mailing, commands=["mailing"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(get_mailings, commands=["mailings"], state="*", is_admin=True, is_private=True)
    dp.register_message_handler(print_single_mailings, commands=["single_mailings"], state="*", is_admin=True,
                                is_private=True)
    dp.register_message_handler(add_mailing_start, commands=["add_mailing"], state="*", is_admin=True)
    dp.register_message_handler(add_group_mailing_start, commands=["add_group_mailing"], state="*", is_admin=True)
    dp.register_message_handler(add_mailing_post, state=GetMailing.mailing, content_types=ContentTypes.ANY,
                                is_private=True)
    dp.register_message_handler(add_mailing_time, state=GetMailing.set_time, content_types=ContentTypes.ANY,
                                is_private=True)

    dp.register_message_handler(add_single_group_mailing_start, commands=["add_single_mailing"], state="*",
                                is_admin=True)
    dp.register_message_handler(add_single_group_mailing_post, state=AddMailingSingle.post_id,
                                content_types=ContentTypes.ANY,
                                is_private=True)
    dp.register_message_handler(add_single_group_mailing_id, state=AddMailingSingle.group_id,
                                content_types=ContentTypes.ANY,
                                is_private=True)

    dp.register_callback_query_handler(cancel, state="*", text_contains='cancel:')
    dp.register_callback_query_handler(mailing_choice_callback, text_contains='mailing_choice:', state='*',
                                       is_private=True, is_admin=True)
    dp.register_callback_query_handler(delete_single_group_mailing_callback,
                                       text_contains='delete_single_group_mailing:', state='*',
                                       is_private=True, is_admin=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
