import json

import aioredis
import asyncio


class Redis:
    def __init__(self, connection_string="redis://localhost"):
        self.r = aioredis.from_url(connection_string)

    async def get_captcha(self, user_id: int) -> dict | bool:
        elements = list(await self.r.smembers('captcha'))
        for i in elements:
            captcha = json.loads(i)
            if captcha['user_id'] == user_id:
                return captcha
        return False

    async def get_captcha_text(self, user_id: int) -> str:
        return (await self.get_captcha(user_id))['text']

    async def add_or_update_captcha(self, user_id: int, text: str) -> None:
        is_captcha = bool(await self.get_captcha(user_id))
        if is_captcha:
            await self.delete_captcha(user_id)

        captcha = json.dumps({'user_id': user_id, 'text': text})
        await self.r.sadd('captcha', captcha)

    async def delete_captcha(self, user_id: int) -> None:
        captcha = await self.get_captcha(user_id)
        await self.r.srem('captcha', json.dumps(captcha))


async def main():
    redis = Redis()
    # await redis.add_captcha(54321, '194234длоапывд')
    print(await redis.delete_captcha(54321))


if __name__ == '__main__':
    asyncio.run(main())
