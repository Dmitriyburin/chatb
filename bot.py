import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from tgbot.models.database import Database

from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admin import register_admin
from tgbot.handlers.echo import register_echo
from tgbot.handlers.user import register_user
from tgbot.handlers.payment_system import payments_controller
from tgbot.handlers.mailing import mailing_controller
from tgbot.handlers.channels import register_channels
from tgbot.handlers.mailing import register_mailing
from tgbot.middlewares.environment import EnvironmentMiddleware
from tgbot.middlewares.bigfather import BigFatherMiddleware

logger = logging.getLogger(__name__)


def register_all_middlewares(dp, config):
    dp.setup_middleware(EnvironmentMiddleware(config=config))
    dp.setup_middleware(BigFatherMiddleware())


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_admin(dp)
    register_user(dp)
    register_channels(dp)
    register_mailing(dp)

    register_echo(dp)


def create_database(config_db):
    database = Database(config_db.string_connection_mongodb)
    return database


def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")
    config = load_config(".env")

    loop = asyncio.get_event_loop()
    storage = RedisStorage2(host='redis') if config.tg_bot.use_redis else MemoryStorage()
    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage, loop=loop)

    bot['config'] = config
    bot['misc'] = config.misc
    bot['db'] = create_database(config.db)

    db: Database = bot['db']
    loop.run_until_complete(db.create_stats_if_not_exist())

    register_all_middlewares(dp, config)
    register_all_filters(dp)
    register_all_handlers(dp)

    dp.loop.create_task(payments_controller(bot, 10))
    dp.loop.create_task(mailing_controller(bot, 1))

    # start
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
