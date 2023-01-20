import datetime
import logging
import time
import heapq

from motor import motor_asyncio
import asyncio

from pymongo import DeleteOne


class Database:
    def __init__(self, connection_mongodb):
        self.cluster = motor_asyncio.AsyncIOMotorClient(connection_mongodb)
        self.db = self.cluster.relation_chat_bot
        self.users = self.db.users
        self.ref_links = self.db.ref_links
        self.chats = self.db.chats
        self.channels = self.db.channels
        self.mailing = self.db.mailing
        self.mailing_users = self.db.mailing_users
        self.banned_users = self.db.banned_users
        self.payments = self.db.payments
        self.stats = self.db.stats
        self.users_chats = self.db.users_chats
        self.dead_users = self.db.dead_users
        self.dead_groups = self.db.dead_groups

    async def add_user(self, user_id, ref, lang='ru') -> None:
        await self.increment_users_count_stats()

        await self.users.insert_one({'user_id': user_id, 'ref': ref, 'lang': lang})

    async def get_user(self, user_id) -> dict:
        return await self.users.find_one({'user_id': user_id})

    async def get_users(self) -> list[dict | None]:
        return [i async for i in self.users.find({})]

    async def get_users_count(self) -> int:
        return await self.users.count_documents({})

    async def increment_subs_ref_commercial(self, ref, count_subs) -> None:
        await self.ref_links.update_one({'ref': ref}, {'$inc': {'subs': count_subs}})

    async def get_mailing(self, message_id) -> dict:
        return await self.mailing.find_one({'message_id': message_id})

    async def get_mailings(self) -> list[dict | None]:
        return [i async for i in self.mailing.find({})]

    async def get_mailing_users(self) -> list[dict | None]:
        users = [user['user_id'] async for user in self.mailing_users.find({}).limit(29)]

        if users:
            requests = [DeleteOne({'user_id': i}) for i in users]
            await self.mailing_users.bulk_write(requests)

        return users

    async def get_mailing_groups(self) -> list[dict | None]:
        groups = [chat['chat_id'] async for chat in self.mailing_users.find({}).limit(29)]

        if groups:
            requests = [DeleteOne({'chat_id': i}) for i in groups]
            await self.mailing_users.bulk_write(requests)

        return groups

    async def get_mailing_ignore(self) -> list:
        return []

    async def update_users_mailing(self, is_group=False) -> None:
        await self.mailing_users.delete_many({})
        if not is_group:
            mailing_ignore = await self.get_mailing_ignore()
            mailing_users = [{'user_id': user['user_id']} for user in await self.get_users() if
                             user['user_id'] not in mailing_ignore]
            await self.mailing_users.insert_many(mailing_users)
        else:
            mailing_users = [{'chat_id': chat['chat_id']} async for chat in self.chats.find({})]
            logging.info(mailing_users)
            await self.mailing_users.insert_many(mailing_users)

    async def add_mailing(self, chat_id, message_id, markup, details, date, is_group=False) -> None:
        await self.mailing.insert_one(
            {'message_id': message_id, 'chat_id': chat_id, 'markup': markup, 'users_count': None,
             'details': details, 'date': date, 'sent': 0, 'not_sent': 0, 'is_active': False, 'is_group': is_group})

    async def reset_mailing_date(self, message_id) -> None:
        await self.mailing.update_one({'message_id': message_id}, {'$set': {'date': None}}, upsert=False)

    async def edit_mailing_progress(self, message_id, sent=0, not_sent=0) -> None:
        await self.mailing.update_one({'message_id': message_id}, {'$inc': {'sent': sent, 'not_sent': not_sent}},
                                      upsert=False)

    async def del_mailing(self, message_id) -> None:
        await self.mailing.delete_many({'message_id': message_id})
        await self.update_users_mailing()

    async def set_active_mailing(self, message_id, is_active, is_group=False) -> None:
        await self.update_users_mailing(is_group=is_group)
        mailing_users_count = await self.mailing_users.count_documents({})

        await self.mailing.update_one({'message_id': message_id},
                                      {'$set': {'is_active': is_active, 'users_count': mailing_users_count}},
                                      upsert=False)

    async def add_channel(self, channel_id, link, is_main=False) -> None:
        await self.channels.insert_one({'channel_id': channel_id, 'link': link, 'is_main': is_main})

    async def del_channel(self, link) -> None:
        await self.channels.delete_one({'link': link})

    async def get_channels(self) -> list[dict | None]:
        return [i async for i in self.channels.find({})]

    async def get_channel(self, link) -> dict:
        return await self.channels.find_one({'link': link})

    async def ban_user(self, user_id, date=None) -> None:
        banned_users = await self.get_ban_users()
        banned_users_ids = [i['user_id'] for i in banned_users]
        if user_id not in banned_users_ids:
            self.banned_users.insert_one({'user_id': int(user_id), 'date': date})

    async def unban_user(self, user_id) -> None:
        await self.banned_users.delete_one({'user_id': user_id})

    async def get_ban_users(self) -> list[dict | None]:
        return [i async for i in self.banned_users.find({})]

    async def get_ban_user(self, user_id) -> dict:
        return self.banned_users.find_one({'user_id': user_id})

    async def add_ref(self, ref, price, contact, date) -> None:
        await self.ref_links.insert_one(
            {'ref': ref, 'users': 0, 'contact': contact, 'date': date, 'transitions': 0, 'price': price,
             'donaters': 0, 'all_price': 0, 'users_channel': []})

    async def add_user_channel_to_ref_if_not_exists(self, ref, user_id: int) -> None:
        await self.ref_links.update_one(
            {'ref': ref}, {'$addToSet': {'users_channel': user_id}})

    async def increment_ref_transition(self, ref) -> None:
        await self.ref_links.update_one({'ref': ref},
                                        {'$inc': {'transitions': 1}},
                                        upsert=False)

    async def add_ref_donater(self, ref, price) -> None:
        await self.ref_links.update_one({'ref': ref},
                                        {'$inc': {'donaters': 1, 'all_price': price}},
                                        upsert=False)

    async def get_refs(self) -> list[dict | None]:
        return [i async for i in self.ref_links.find({})]

    async def get_ref(self, ref) -> dict:
        return await self.ref_links.find_one({'ref': ref})

    async def delete_ref(self, ref) -> None:
        await self.ref_links.delete_one({'ref': ref})

    async def ref_stats(self, ref) -> dict:
        all_users = await self.users.count_documents(
            {'ref': ref}
        )

        return {'all_users': all_users}

    async def get_is_ref_commercial(self, ref) -> bool:
        refs_list = list(map(lambda x: x['ref'], await self.get_refs()))
        return True if ref in refs_list else False

    @staticmethod
    async def get_anypay_payment_id() -> int:
        return int(time.time() * 10000)

    async def add_anypay_payment(self, user_id, sign, secret, payment_id, price, action=None) -> None:
        await self.payments.insert_one(
            {'type': 'anypay', 'user_id': user_id, 'sign': sign, 'secret': secret, 'payment_id': payment_id,
             'price': float(price), 'paid': False, 'gived': False, 'action': action})

    async def get_payment_by_secret(self, secret) -> dict:
        return await self.payments.find_one({'secret': secret})

    async def edit_paid_status(self, secret) -> None:
        await self.payments.update_one({'secret': secret}, {'$set': {'paid': True, 'discount': None}}, upsert=False)

    async def edit_given_status(self, secret) -> None:
        await self.payments.update_one({'secret': secret}, {'$set': {'gived': True}}, upsert=False)

    async def get_ungiven_payments(self) -> list[dict | None]:
        await self.payments.delete_many({'gived': True, 'paid': True})
        return [i async for i in self.payments.find({'gived': False, 'paid': True})]

    async def get_stats(self) -> dict:
        stats = await self.stats.find_one({'stats': 'all'})
        return stats

    async def get_stats_real(self) -> dict:
        all_users = await self.users.count_documents({})
        all_chats = await self.chats.count_documents({})
        all_chats_users = await self.users_chats.count_documents({})
        dead_groups = await self.dead_groups.count_documents({})
        return {'all_users': all_users, 'all_chats': all_chats, 'all_chats_users': all_chats_users,
                'dead_groups': dead_groups}

    async def create_stats_if_not_exist(self) -> None:
        if await self.get_stats():
            return

        users_count = await self.get_users_count()
        await self.stats.insert_one({'stats': 'all', 'price': 0, 'users_count': users_count})

    async def increment_price_stats(self, price) -> None:
        await self.stats.update_one({'stats': 'all'}, {'$inc': {'price': price}})

    async def increment_users_count_stats(self) -> None:
        await self.stats.update_one({'stats': 'all'}, {'$inc': {'users_count': 1}})

    # Chat
    async def add_chat_user(self, chat_id: int, user_id: int) -> None:
        time_registration = datetime.datetime.now().timestamp()
        user = {'user_id': user_id, 'time_registration': time_registration, 'description': '-',
                'main_relation': None}
        await self.chats.update_one({'chat_id': chat_id}, {'$push': {'users': user}})

    async def add_user_if_not_exists(self, chat_id: int, user_id: int) -> None:
        user = await self.get_chat_user(chat_id, user_id)
        if not user:
            await self.add_chat_user(chat_id, user_id)

    async def get_chat_user(self, chat_id: int, user_id: int) -> dict | bool:
        # users_chat = (await self.get_chat(chat_id))['users']
        # for user in users_chat:
        #     if user['user_id'] == user_id:
        #         return user
        # db.chats.find({'chat_id': -788548753, 'users.user_id': 865351408}, {_id: 0, users: { $elemMatch: {
        #     user_id: 865351408}}});

        chat_user = (await self.chats.find_one(
            {'chat_id': chat_id, 'users': {'$elemMatch': {'user_id': user_id}}}))
        if not chat_user:
            return chat_user
        return chat_user['users'][0]

    async def add_chat(self, chat_id: int) -> None:
        await self.chats.insert_one(
            {'chat_id': chat_id, 'users': [], 'relations': []})

    async def get_chat(self, chat_id: int) -> dict | bool:
        return await self.chats.find_one({'chat_id': chat_id})

    async def get_chats(self):
        return self.chats.find({})

    async def add_chat_if_not_exists(self, chat_id: int):
        if not await self.get_chat(chat_id):
            await self.add_chat(chat_id)

    async def add_relation(self, chat_id: int, user1_id: int, user2_id: int) -> None:
        if not await self.get_chat_user(chat_id, user1_id):
            await self.add_chat_user(chat_id, user1_id)

        if not await self.get_chat_user(chat_id, user2_id):
            await self.add_chat_user(chat_id, user2_id)
        time_registration = datetime.datetime.now().timestamp()
        relation = {'users': [user1_id, user2_id], 'hp': 0,
                    'time_registration': time_registration, 'time_to_next_action': None}
        await self.chats.update_one({'chat_id': chat_id}, {'$push': {'relations': relation}})

    async def delete_relation(self, chat_id: int, user1_id: int, user2_id: int) -> None:
        relations = (await self.get_chat(chat_id))['relations']
        for i, relation in enumerate(relations):
            if set(relation['users']) == {user1_id, user2_id}:
                if (await self.get_main_relation(chat_id, user1_id)) == user2_id:
                    await self.chats.update_one(
                        {'chat_id': chat_id, 'users.user_id': user1_id},
                        {'$set': {'users.$.main_relation': None}})
                if (await self.get_main_relation(chat_id, user2_id)) == user1_id:
                    await self.chats.update_one(
                        {'chat_id': chat_id, 'users.user_id': user2_id},
                        {'$set': {'users.$.main_relation': None}})

                await self.chats.update_one({'chat_id': chat_id},
                                            {'$pull': {'relations': {'users': [user1_id, user2_id]}}})
                await self.chats.update_one({'chat_id': chat_id},
                                            {'$pull': {'relations': {'users': [user2_id, user1_id]}}})

    async def get_relation(self, chat_id: int, user1_id: int, user2_id: int) -> dict | bool:
        relations = (await self.get_chat(chat_id))['relations']
        for relation in relations:
            if set(relation['users']) == {user1_id, user2_id}:
                return relation

    async def get_best_hp_relations(self, chat_id: int, count=10):
        relations_iter = iter((await self.get_chat(chat_id))['relations'])
        return heapq.nlargest(count, relations_iter, key=lambda x: x['hp'])

    async def get_best_time_relations(self, chat_id: int, count=10):
        relations_iter = iter((await self.get_chat(chat_id))['relations'])
        return heapq.nsmallest(count, relations_iter, key=lambda x: x['time_registration'])

    async def get_main_relation(self, chat_id: int, user_id: int) -> dict | bool:
        return (await self.get_chat_user(chat_id, user_id))['main_relation']

    async def get_user_relations(self, chat_id: int, user_id: int) -> list | bool:
        relations = (await self.get_chat(chat_id))['relations']
        return [relation for relation in relations if user_id in relation['users']]

    async def edit_main_relation(self, chat_id: int, user1_id: int, user2_id: int | None) -> None:
        await self.chats.update_one(
            {'chat_id': chat_id, 'users.user_id': user1_id},
            {'$set': {'users.$.main_relation': user2_id}})

    async def edit_description(self, chat_id: int, user_id: int, description: str) -> None:
        await self.chats.update_one(
            {'chat_id': chat_id, 'users.user_id': user_id},
            {'$set': {'users.$.description': description}})

    async def edit_time_last_farm(self, user_id: int) -> None:
        await self.users_chats.update_one(
            {'user_id': user_id},
            {'$set': {'time_last_farm': datetime.datetime.now().timestamp()}})

    async def make_action(self, chat_id: int, user1_id: int, user2_id: int, hp: int, delta_to_next_action: int,
                          free=True, coins=0):
        if free:
            time_to_next_action = (
                    datetime.datetime.now() + datetime.timedelta(minutes=delta_to_next_action)).timestamp()
            await self.chats.update_one({'chat_id': chat_id, 'relations.users': [user1_id, user2_id]},
                                        {'$inc': {'relations.$.hp': hp},
                                         '$set': {'relations.$.time_to_next_action': time_to_next_action}})

            await self.chats.update_one({'chat_id': chat_id, 'relations.users': [user2_id, user1_id]},
                                        {'$inc': {'relations.$.hp': hp},
                                         '$set': {'relations.$.time_to_next_action': time_to_next_action}})
        else:
            await self.chats.update_one({'chat_id': chat_id, 'relations.users': [user1_id, user2_id]},
                                        {'$inc': {'relations.$.hp': hp}})

            await self.chats.update_one({'chat_id': chat_id, 'relations.users': [user2_id, user1_id]},
                                        {'$inc': {'relations.$.hp': hp}})
            await self._decrease_coins(user1_id, coins)

    # async def _increment_relation_hp(self, chat_id: int, user1_id: int, user2_id: int, hp: int):
    async def _decrease_coins(self, user_id: int, coins: int) -> None:
        await self.users_chats.update_one(
            {'user_id': user_id},
            {'$inc': {'coins': -coins}})

    async def increase_coins(self, user_id: int, coins: int) -> None:
        await self.users_chats.update_one(
            {'user_id': user_id},
            {'$inc': {'coins': coins}})

    async def add_user_chats(self, user_id: int, username=None) -> None:
        await self.users_chats.insert_one(
            {'user_id': user_id, 'username': username, 'hours_to_next_farm': 4, 'coins': 0,
             'time_last_farm': None})

    async def get_user_chats(self, user_id: int) -> dict:
        return await self.users_chats.find_one({'user_id': user_id})

    async def get_users_chats(self):
        return self.users_chats.find({})

    async def get_3_hours_farm_users_chats(self):
        return self.users_chats.find({'hours_to_next_farm': 3})

    async def add_user_chats_if_not_exists(self, user_id: int, username=None):
        if not await self.get_user_chats(user_id):
            await self.add_user_chats(user_id, username=username)

    async def update_username_if_update(self, user_id: int, username):
        if (await self.get_user_chats(user_id)).get('username') != username:
            await self.users_chats.update_one(
                {'user_id': user_id},
                {'$set': {'username': username}})

    async def get_id_by_username(self, username: str):
        users_chats = await self.get_users_chats()
        async for user in users_chats:
            if user.get('username'):
                if user['username'].lower() == username.lower():
                    return user['user_id']

    async def get_main_channel(self) -> dict:
        return await self.channels.find_one({'is_main': True})

    async def set_hours_for_next_time(self, user_id: int, hours: int):
        await self.users_chats.update_one(
            {'user_id': user_id},
            {'$set': {'hours_to_next_farm': hours}})

    async def add_dead_user(self, user_id) -> None:
        if not await self.get_dead_user(user_id):
            await self.dead_users.insert_one({'user_id': user_id})

    async def delete_dead_user(self, user_id) -> None:
        await self.dead_users.delete_many({'user_id': user_id})

    async def get_dead_user(self, user_id) -> None:
        await self.dead_users.find_one({'user_id': user_id})

    async def add_dead_groups(self, group_id) -> None:
        if not await self.get_dead_groups(group_id):
            await self.dead_groups.insert_one({'group_id': group_id})

    async def delete_dead_groups(self, group_id) -> None:
        await self.dead_groups.delete_many({'group_id': group_id})

    async def get_dead_groups(self, group_id) -> None:
        await self.dead_groups.find_one({'group_id': group_id})


async def main():
    database = Database('mongodb://localhost:27017')
    print(await database.get_chat_user(-788548753, 563579434))


if __name__ == '__main__':
    asyncio.run(main())
