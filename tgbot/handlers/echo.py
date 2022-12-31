from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from tgbot.keyboards import reply


async def bot_echo_all(message: types.Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    await message.answer(texts['not_understand'], reply_markup=reply.main(buttons))


def register_echo(dp: Dispatcher):
    dp.register_message_handler(bot_echo_all, state="*", content_types=types.ContentTypes.ANY)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
