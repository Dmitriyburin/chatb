from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from tgbot.keyboards import reply


async def bot_echo_all(message: types.Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    if message.text == buttons['install']:
        await message.answer(texts['add_bot_to_chat_manual'])
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
