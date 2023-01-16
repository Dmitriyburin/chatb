from aiogram import Dispatcher
from aiogram.types import Message
from tgbot.keyboards import reply, inline
from tgbot.handlers.channels import check_sub, required_channel
from tgbot.handlers.chat import get_nickname
from tgbot.handlers.chat import get_actions, get_relation_dict, get_user_relations, print_user_relations, print_fast_farm


async def user_start(message: Message):
    bot = message.bot
    data = bot['db']
    misc = bot['misc']
    texts = misc.texts
    buttons = misc.buttons

    user = await data.get_user(message.from_user.id)
    ref = None
    if len(message.text.split()) > 1:
        if 'actions' in message.text.split()[1]:
            hp = int(message.text.split()[1].split('_')[1])
            free = message.text.split()[1].split('_')[2]
            free = True if free == 't' else False
            desc = get_relation_dict(misc, hp)['description']
            await message.answer(f'{desc}\n\n{get_actions(misc, hp, free=free)}')
        elif 'relations' in message.text.split()[1]:
            chat_id = int(message.text.split()[1].split('_')[1])
            await print_user_relations(message, 0, chat_id=chat_id)
        elif 'fast_farm' in message.text.split()[1]:
            await print_fast_farm(message)
        else:
            ref = message.text.split()[1]

    if ref and await data.get_is_ref_commercial(ref):
        await data.increment_ref_transition(ref)

    if not user:
        await data.add_user(message.from_user.id, ref)
    link = f'https://t.me/{(await bot.get_me()).username}?startgroup'
    await message.reply(texts['start_text'].format(await get_nickname(message.from_user)),
                        reply_markup=inline.add_bot_to_chat(buttons, link))

    await message.answer(texts['select_action'], reply_markup=reply.main(buttons))

    # white_list = bot['config'].tg_bot.admin_ids
    # user = await data.get_user(message.from_user.id)
    # if message.from_user.id not in white_list and user:
    #     channels = await check_sub(message)
    #     if channels:
    #         await required_channel(message, None)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*", is_private=True)
