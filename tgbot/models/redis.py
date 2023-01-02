import json

import aioredis
import asyncio


class Redis:
    def __init__(self, connection_string="redis://localhost"):
        self.r = aioredis.from_url(connection_string)

    async def get_captcha(self, user_id: int) -> dict | bool:
        generator_captcha = self.r.sscan_iter("captcha")
        async for i in generator_captcha:
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
    await redis.add_or_update_captcha(12313, '12313')
    # print(await redis.delete_captcha(12313))


if __name__ == '__main__':
    asyncio.run(main())
