import random
import string


async def generate_start_ref(data):
    alph = list(string.ascii_lowercase)
    random.shuffle(alph)
    result = alph[:10]

    while result in (await data.get_refs()):
        random.shuffle(alph)
        result = alph[:10]

    return ''.join(result)


async def get_start_url_by_ref(bot, ref):
    bot_name = (await bot.get_me()).username
    return f'https://t.me/{bot_name}?start={ref}'


async def parse_ref_from_link(ref: str):
    return ref.split('=')[-1]
