import typing

from aiogram.dispatcher.filters import BoundFilter
from aiogram import types


class PrivateFilter(BoundFilter):
    key = 'is_private'

    def __init__(self, is_private: typing.Optional[bool] = None):
        self.is_private = is_private

    async def check(self, message: types.Message):
        return message.chat.type == types.ChatType.PRIVATE
