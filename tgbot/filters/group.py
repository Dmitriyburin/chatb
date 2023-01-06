import typing

from aiogram.dispatcher.filters import BoundFilter
from aiogram import types


class GroupFilter(BoundFilter):
    key = 'is_group'

    def __init__(self, is_group: typing.Optional[bool] = None):
        self.is_group = is_group

    async def check(self, message: types.Message):
        return message.chat.type in [types.ChatType.SUPERGROUP, types.ChatType.GROUP]
