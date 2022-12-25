import logging
import asyncio
import datetime
import time

from aiogram.types import Message
from aiogram.dispatcher import FSMContext


async def payments_controller(bot, delay):
    data: Database = bot['db']
    misc = bot['misc']
    texts = misc.texts

    while True:
        await asyncio.sleep(delay)

        ungived = await data.get_ungiven_payments()
        async for i in ungived:
            price = i['price']
            action = i['action']

            if action == 'unban':
                await data.unban_user(i['user_id'])
                await bot.send_message(i['user_id'], texts['unbanned'])

            user = await data.get_user(i['user_id'])
            if await data.get_is_ref_commercial(user['ref']):
                await data.add_ref_donater(user['ref'], price)

            await data.edit_given_status(i['secret'])
            await data.increment_price_stats(i['price'])


if __name__ == '__main__':
    from ..models.database import Database
    from ..config import load_config

    config = load_config("../../.env")
