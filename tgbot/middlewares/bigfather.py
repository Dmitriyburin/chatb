import asyncio

import datetime
import logging
import random

from captcha.image import ImageCaptcha
from aiogram.types import InputFile
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from aiogram.dispatcher import DEFAULT_RATE_LIMIT
from aiogram.dispatcher.handler import CancelHandler, current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils.exceptions import Throttled
from tgbot.keyboards import inline
from tgbot.misc import anypay
from tgbot.handlers.channels import check_sub, required_channel


class BigFatherMiddleware(BaseMiddleware):
    """
    Simple middleware
    """

    def __init__(self, limit=DEFAULT_RATE_LIMIT, key_prefix='antiflood_'):
        self.rate_limit = limit
        self.prefix = key_prefix
        super(BigFatherMiddleware, self).__init__()

    async def on_pre_process_update(self, update: types.Update, data: dict):
        bot = update.bot
        if update.message:
            message = update.message
        elif update.callback_query:
            message = update.callback_query.message

        else:
            return

        bot_data: Database = bot['db']
        if message.chat.type in [types.ChatType.SUPERGROUP, types.ChatType.GROUP]:
            await bot_data.add_user_chats_if_not_exists(message.from_user.id, username=message.from_user.username)
            await bot_data.update_username_if_update(message.from_user.id, username=message.from_user.username)

        if message.chat.type != types.ChatType.PRIVATE:
            return
        misc = bot['misc']
        texts = misc.texts

        # Проверка на бан
        banned_users = await bot_data.get_ban_users()
        for banned_user in banned_users:
            if banned_user['user_id'] == message.from_user.id:
                if banned_user['date']:
                    current_time = datetime.datetime.now()
                    if current_time >= banned_user['date']:
                        await bot_data.unban_user(message.from_user.id)
                    else:
                        remained_seconds = (datetime.datetime.fromtimestamp(banned_user['date']) - current_time).seconds
                        remained_hours = remained_seconds // 3600
                        remained_minutes = (remained_seconds - (remained_hours * 3600)) // 60
                        await message.answer(texts['you_are_banned_time'].format(remained_hours, remained_minutes))
                        raise CancelHandler()
                else:

                    await message.answer(texts['you_are_banned'])
                    raise CancelHandler()

        # Channels
        # if update.callback_query:
        #     return
        #
        # white_list = bot['config'].tg_bot.admin_ids
        # user = await bot_data.get_user(message.from_user.id)
        # if message.from_user.id not in white_list and user:
        #     channels = await check_sub(message)
        #     if channels:
        #         await required_channel(message, None)
        #         raise CancelHandler()

    async def on_process_message(self, message: types.Message, data: dict):
        """
        This handler is called when dispatcher receives a message
        :param message:
        """

        if message.chat.type != types.ChatType.PRIVATE:
            return

        # Get current handler
        handler = current_handler.get()

        # Get dispatcher from context
        dispatcher = Dispatcher.get_current()

        # If handler was configured, get rate limit and key from handler
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        # Use Dispatcher.throttle method.
        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            # Execute action
            await self.message_throttled(message, t)

            # Cancel current handler
            raise CancelHandler()

    async def message_throttled(self, message: types.Message, throttled: Throttled):
        """
        Notify user only on first exceed and notify about unlocking only on last exceed
        :param message:
        :param throttled:
        """
        if message.chat.type != types.ChatType.PRIVATE:
            return
        handler = current_handler.get()
        dispatcher = Dispatcher.get_current()
        if handler:
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            key = f"{self.prefix}_message"

        # Calculate how many time is left till the block ends
        delta = throttled.rate - throttled.delta
        bot = message.bot

        # # Prevent flooding
        # if throttled.exceeded_count <= 2:
        #     await generate_captcha(bot, message)

        # Sleep.
        await asyncio.sleep(delta)

        # Check lock status
        thr = await dispatcher.check_key(key)

        # If current message is not last with current key - do not send message
        if thr.exceeded_count == throttled.exceeded_count:
            print('время прошло')


def wrap_media(bytesio, **kwargs):
    """Wraps plain BytesIO objects into InputMediaPhoto"""
    bytesio.seek(0)
    return types.InputMediaPhoto(types.InputFile(bytesio), **kwargs)


async def generate_captcha(bot, message, edit=False):
    image = ImageCaptcha(width=250, height=100)
    nums = list([str(i) for i in list(range(0, 7)) + list(range(8, 10))])
    random.shuffle(nums)
    captcha_text = ''.join(nums[:4])
    data = image.generate(captcha_text)

    redis: Redis = bot['redis']
    await redis.add_or_update_captcha(message.from_user.id, captcha_text)

    await message.answer_photo(data, caption='Введите текст с картинки')


if __name__ == '__main__':
    from ..misc.functions import generate_start_ref
    from ..models.database import Database
    from ..models.redis import Redis
    from ..config import load_config

    config = load_config("../../.env")
