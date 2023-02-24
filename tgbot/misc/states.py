from aiogram.dispatcher.filters.state import State, StatesGroup


class GetMailing(StatesGroup):
    mailing = State()
    set_time = State()


class AddMailingSingle(StatesGroup):
    post_id = State()
    group_id = State()


class AddChannel(StatesGroup):
    channel = State()
    link = State()


class DeleteChannel(StatesGroup):
    channel = State()


class AddRef(StatesGroup):
    date = State()
    price = State()
    contact = State()


class DeleteRef(StatesGroup):
    ref = State()


class StatsRef(StatesGroup):
    ref = State()


class BanUser(StatesGroup):
    user_id = State()


class UnbanUser(StatesGroup):
    user_id = State()


class RefsMonth(StatesGroup):
    month_callback = State()


class RequiredChannel(StatesGroup):
    required_channel = State()


class Captcha(StatesGroup):
    enter_captcha = State()


class EditDescription(StatesGroup):
    description = State()


class ExtraditionMoney(StatesGroup):
    chat_id = State()
    user_id = State()
    count = State()


class AddUsers(StatesGroup):
    file = State()
