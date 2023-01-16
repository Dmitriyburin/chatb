import asyncio
import logging

from aiogram import Dispatcher
from aiogram.types import Message, ChatMemberUpdated, ChatMember, CallbackQuery
from tgbot.keyboards import inline


async def add_to_chat(event: ChatMemberUpdated):
    bot = event.bot
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons
    logging.info(event)
    if event.new_chat_member.user.id == bot.id and event.old_chat_member.status in ['left', 'kicked']:
        await asyncio.sleep(1)
        status = (await bot.get_chat_member(event.chat.id, bot.id)).status
        # status = event.new_chat_member.status
        if status == 'administrator':
            await bot.send_message(event.chat.id, texts['bot_add_to_chat_with_admin'])
        elif status == 'member':
            await bot.send_message(event.chat.id, texts['bot_add_to_chat_without_admin'],
                                   reply_markup=inline.done(buttons, 'check_admin_roots'))
        await data.delete_dead_groups(event.chat.id)
    elif event.new_chat_member.user.id == bot.id and event.old_chat_member.status in ['administrator', 'member']:
        status = event.new_chat_member.status
        if status in ['left', 'kicked']:
            await data.add_dead_groups(event.chat.id)


async def check_admin_roots(call: CallbackQuery):
    bot = call.bot
    message = call.message
    message.from_user.id = call['from']['id']
    message.from_user.username = call['from']['username']
    misc = bot['misc']
    texts = misc.texts

    status = (await bot.get_chat_member(message.chat.id, bot.id)).status
    if status != 'administrator':
        await call.bot.answer_callback_query(call.id)
        return
    await message.answer(texts['get_admin_roots'])
    await message.delete()
    await call.bot.answer_callback_query(call.id)


async def chat_member(event: ChatMemberUpdated):
    logging.info(event)


def register_add_to_chat(dp: Dispatcher):
    dp.register_my_chat_member_handler(add_to_chat, is_group=True)
    dp.register_chat_member_handler(chat_member)
    dp.register_callback_query_handler(check_admin_roots,
                                       text_contains='check_admin_roots')


if __name__ == '__main__':
    from ..misc.functions import generate_start_ref
    from ..models.database import Database
