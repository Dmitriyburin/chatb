from aiogram import Dispatcher
from aiogram.types import Message
from tgbot.keyboards import reply
from tgbot.handlers.channels import check_sub, required_channel


async def user_start(message: Message):
    bot = message.bot
    data = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = await data.get_user(message.from_user.id)
    ref = None if message.text == '/start' else message.text.split()[1]
    if await data.get_is_ref_commercial(ref):
        await data.increment_ref_transition(ref)

    if not user:
        await data.add_user(message.from_user.id, ref)
        await message.reply(texts['start_text'], reply_markup=reply.main(buttons))
    else:
        await message.reply(texts['start_text'], reply_markup=reply.main(buttons))

    white_list = bot['config'].tg_bot.admin_ids
    user = await data.get_user(message.from_user.id)
    if message.from_user.id not in white_list and user:
        channels = await check_sub(message)
        if channels:
            await required_channel(message, None)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
