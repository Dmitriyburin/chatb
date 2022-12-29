import datetime
import time

from motor import motor_asyncio
import asyncio

from pymongo import DeleteOne


class Database:
    def __init__(self, connection_mongodb):
        self.cluster = motor_asyncio.AsyncIOMotorClient(connection_mongodb)
        self.db = self.cluster.newtemplate
        self.users = self.db.users
        self.ref_links = self.db.ref_links
        self.channels = self.db.channels
        self.mailing = self.db.mailing
        self.mailing_users = self.db.mailing_users
        self.banned_users = self.db.banned_users
        self.payments = self.db.payments
        self.stats = self.db.stats

    async def add_user(self, user_id, ref, lang='ru') -> None:
        await self.increment_users_count_stats()

        await self.users.insert_one({'user_id': user_id, 'ref': ref, 'lang': lang})

    async def get_user(self, user_id):
        return await self.users.find_one({'user_id': user_id})

    async def get_users(self):
        return self.users.find({})

    async def get_users_count(self):
        return await self.users.count_documents({})

    async def increment_subs_ref_commercial(self, ref, count_subs) -> None:
        await self.ref_links.update_one({'ref': ref}, {'$inc': {'subs': count_subs}})

    async def get_mailing(self, message_id):
        return await self.mailing.find_one({'message_id': message_id})

    async def get_mailings(self):
        return [i async for i in self.mailing.find({})]

    async def get_mailing_users(self):
        users = [user['user_id'] async for user in self.mailing_users.find({}).limit(29)]

        if users:
            requests = [DeleteOne({'user_id': i}) for i in users]
            await self.mailing_users.bulk_write(requests)

        return users

    async def get_mailing_ignore(self):
        return []

    async def update_users_mailing(self) -> None:
        await self.mailing_users.delete_many({})
        mailing_ignore = await self.get_mailing_ignore()
        mailing_users = [{'user_id': user['user_id']} async for user in await self.get_users() if
                         user['user_id'] not in mailing_ignore]
        await self.mailing_users.insert_many(mailing_users)

    async def add_mailing(self, chat_id, message_id, markup, details, date) -> None:
        await self.mailing.insert_one(
            {'message_id': message_id, 'chat_id': chat_id, 'markup': markup, 'users_count': None,
             'details': details, 'date': date, 'sent': 0, 'not_sent': 0, 'is_active': False})

    async def reset_mailing_date(self, message_id) -> None:
        await self.mailing.update_one({'message_id': message_id}, {'$set': {'date': None}}, upsert=False)

    async def edit_mailing_progress(self, message_id, sent=0, not_sent=0) -> None:
        await self.mailing.update_one({'message_id': message_id}, {'$inc': {'sent': sent, 'not_sent': not_sent}},
                                      upsert=False)

    async def del_mailing(self, message_id) -> None:
        await self.mailing.delete_many({'message_id': message_id})
        await self.update_users_mailing()

    async def set_active_mailing(self, message_id, is_active) -> None:
        await self.update_users_mailing()
        mailing_users_count = await self.mailing_users.count_documents({})

        await self.mailing.update_one({'message_id': message_id},
                                      {'$set': {'is_active': is_active, 'users_count': mailing_users_count}},
                                      upsert=False)

    async def add_channel(self, channel_id, link) -> None:
        await self.channels.insert_one({'channel_id': channel_id, 'link': link})

    async def del_channel(self, link) -> None:
        await self.channels.delete_one({'link': link})

    async def get_channels(self):
        return [i async for i in self.channels.find({})]

    async def get_channel(self, link):
        return await self.channels.find_one({'link': link})

    async def ban_user(self, user_id, date=None) -> None:
        banned_users = await self.get_ban_users()
        banned_users_ids = [i['user_id'] for i in banned_users]
        if user_id not in banned_users_ids:
            self.banned_users.insert_one({'user_id': int(user_id), 'date': date})

    async def unban_user(self, user_id) -> None:
        await self.banned_users.delete_one({'user_id': user_id})

    async def get_ban_users(self):
        return [i async for i in self.banned_users.find({})]

    async def get_ban_user(self, user_id):
        return self.banned_users.find_one({'user_id': user_id})

    async def add_ref(self, ref, price, contact, date) -> None:
        await self.ref_links.insert_one(
            {'ref': ref, 'users': 0, 'contact': contact, 'date': date, 'transitions': 0, 'price': price,
             'donaters': 0, 'all_price': 0})

    async def increment_ref_transition(self, ref) -> None:
        await self.ref_links.update_one({'ref': ref},
                                        {'$inc': {'transitions': 1}},
                                        upsert=False)

    async def add_ref_donater(self, ref, price) -> None:
        await self.ref_links.update_one({'ref': ref},
                                        {'$inc': {'donaters': 1, 'all_price': price}},
                                        upsert=False)

    async def get_refs(self):
        return [i async for i in self.ref_links.find({})]

    async def get_ref(self, ref):
        return await self.ref_links.find_one({'ref': ref})

    async def delete_ref(self, ref) -> None:
        await self.ref_links.delete_one({'ref': ref})

    async def ref_stats(self, ref):
        all_users = await self.users.count_documents(
            {'ref': ref}
        )

        return {'all_users': all_users}

    async def get_is_ref_commercial(self, ref) -> bool:
        refs_list = list(map(lambda x: x['ref'], await self.get_refs()))
        return True if ref in refs_list else False

    @staticmethod
    async def get_anypay_payment_id():
        return int(time.time() * 10000)

    async def add_anypay_payment(self, user_id, sign, secret, payment_id, price, action=None) -> None:
        await self.payments.insert_one(
            {'type': 'anypay', 'user_id': user_id, 'sign': sign, 'secret': secret, 'payment_id': payment_id,
             'price': float(price), 'paid': False, 'gived': False, 'action': action})

    async def get_payment_by_secret(self, secret):
        return await self.payments.find_one({'secret': secret})

    async def edit_paid_status(self, secret) -> None:
        await self.payments.update_one({'secret': secret}, {'$set': {'paid': True, 'discount': None}}, upsert=False)

    async def edit_given_status(self, secret) -> None:
        await self.payments.update_one({'secret': secret}, {'$set': {'gived': True}}, upsert=False)

    async def get_ungiven_payments(self):
        await self.payments.delete_many({'gived': True, 'paid': True})
        return self.payments.find({'gived': False, 'paid': True})

    async def get_stats(self):
        stats = await self.stats.find_one({'stats': 'all'})
        return stats

    async def create_stats_if_not_exist(self):
        if await self.get_stats():
            return

        users_count = await self.get_users_count()
        await self.stats.insert_one({'stats': 'all', 'price': 0, 'users_count': users_count})

    async def increment_price_stats(self, price):
        await self.stats.update_one({'stats': 'all'}, {'$inc': {'price': price}})

    async def increment_users_count_stats(self):
        await self.stats.update_one({'stats': 'all'}, {'$inc': {'users_count': 1}})


async def main():
    database = Database('mongodb://localhost:27017')


if __name__ == '__main__':
    asyncio.run(main())
