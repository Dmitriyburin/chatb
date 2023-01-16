from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from tgbot.keyboards import reply, inline
from tgbot.handlers.channels import check_sub, required_channel


async def bot_echo_all(message: types.Message, state: FSMContext):
    bot = message.bot
    data = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    if message.text in [buttons['install'], buttons['help']]:
        white_list = bot['config'].tg_bot.admin_ids
        user = await data.get_user(message.from_user.id)
        if message.from_user.id not in white_list and user:
            channels = await check_sub(message)
            if channels:
                await required_channel(message, None)
                return

    if message.text == buttons['install']:
        link = f'https://t.me/{(await bot.get_me()).username}?startgroup'
        await message.answer(texts['add_bot_to_chat_manual'], reply_markup=inline.add_bot_to_chat(buttons, link))
        return
    elif message.text == buttons['help']:
        await message.answer(texts['in_development'])
        return

    await message.answer(texts['not_understand'], reply_markup=reply.main(buttons))


def register_echo(dp: Dispatcher):
    dp.register_message_handler(bot_echo_all, state="*", content_types=types.ContentTypes.ANY, is_private=True)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
