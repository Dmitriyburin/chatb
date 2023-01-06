import logging

from aiogram import Dispatcher
from aiogram.types import Message, ChatMemberUpdated, ChatMember, CallbackQuery
from tgbot.keyboards import inline


async def add_to_chat(event: ChatMemberUpdated):
    bot = event.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons
    logging.info(event)
    if event.new_chat_member.user.id == bot.id and event.old_chat_member.status in ['left', 'kicked']:
        status = event.new_chat_member.status
        if status == 'administrator':
            await bot.send_message(event.chat.id, texts['bot_add_to_chat_with_admin'])
        elif status == 'member':
            await bot.send_message(event.chat.id, texts['bot_add_to_chat_without_admin'],
                                   reply_markup=inline.done(buttons, 'check_admin_roots'))


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


def register_add_to_chat(dp: Dispatcher):
    dp.register_my_chat_member_handler(add_to_chat)
    dp.register_callback_query_handler(check_admin_roots,
                                       text_contains='check_admin_roots')