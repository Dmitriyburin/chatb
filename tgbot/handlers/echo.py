from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.utils.markdown import hcode


async def bot_echo_all(message: types.Message, state: FSMContext):
    bot = message.bot
    misc = bot['misc']
    data: Database = bot['db']
    texts = misc.texts

    await message.answer(texts['not_understand'])


def register_echo(dp: Dispatcher):
    dp.register_message_handler(bot_echo_all, state="*", content_types=types.ContentTypes.ANY)


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
