from dataclasses import dataclass
from pprint import pprint
from typing import TypedDict
from environs import Env
from yaml import safe_load


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str
    string_connection_mongodb: str
    string_connection_redis: str


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    use_redis: bool


@dataclass
class Anypay:
    secret: str
    shop: int


@dataclass
class Pyrogram:
    api_id: int
    api_hash: str


@dataclass
class Miscellaneous:
    texts: TypedDict
    buttons: dict
    prices: dict
    anypay: Anypay
    payment_token: str
    relations: dict
    commands: dict
    botstat_key: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    misc: Miscellaneous


def load_config(path: str = None):
    env = Env()
    env.read_env(path)
    with open('tgbot/config.yaml', encoding='utf-8') as f:
        conf = safe_load(f)
        return Config(
            tg_bot=TgBot(
                token=env.str("BOT_TOKEN"),
                admin_ids=list(map(int, env.list("ADMINS"))),
                use_redis=env.bool("USE_REDIS"),
            ),
            db=DbConfig(
                host=env.str('DB_HOST'),
                password=env.str('DB_PASS'),
                user=env.str('DB_USER'),
                database=env.str('DB_NAME'),
                string_connection_mongodb=env.str('STRING_CONNECTION_MONGODB'),
                string_connection_redis=env.str('STRING_CONNECTION_REDIS')
            ),
            misc=Miscellaneous(
                texts=conf['texts'],
                buttons=conf['buttons'],
                prices=conf['prices'],
                anypay=Anypay(
                    secret=env.str('ANYPAY_SECRET'),
                    shop=env.str('ANYPAY_SHOP')),
                payment_token=env.str('PAYMENT_TOKEN'),
                relations=conf['relations'],
                commands=conf['commands'],
                botstat_key=env.str('API_BOTSTAT_KEY')
            ),
        )


if __name__ == '__main__':
    with open('./config.yaml', encoding='utf-8') as f:
        conf = safe_load(f)
        pprint(conf['commands'])
