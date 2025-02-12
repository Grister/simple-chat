from .base import BaseConsumer
from channels.db import database_sync_to_async
from chat.models import ChatRoomModel, ParticipantModel, MessageModel, UserModel


class ChatRoomConsumer(BaseConsumer):
    async def connect(self):
        await super().connect()
        self.group_id = self.scope['url_route']['kwargs']['chat_room']
        self.group = await self.get_group()
        if not self.group:
            await self._throw_error(message={
                'detail': 'Group not found'
            })
            return await self.close(1000)

        self.participants = await self.get_participants()

        if self.scope['user'] not in self.participants:
            await self._throw_error(message={
                'detail': 'Access denied'
            })
            return await self.close(1000)

        await self.channel_layer.group_add(self.group_id, self.channel_name)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_id, self.channel_name)
        return await super().disconnect(code)

    async def _group_send(self, message):
        await self.channel_layer.group_send(
            self.group_id,
            {
                'type': 'chat.message',
                'message': message,
            }
        )

    @staticmethod
    def creator_permission(func):
        async def wrapper(self, *args, **kwargs):
            creator = await self.get_creator()
            if creator == self.scope['user']:
                return await func(self, *args, **kwargs)
            else:
                return await self._throw_error(
                    message={'detail': 'You do not have permissions to perform this action'},
                )
        return wrapper

    async def chat_message(self, event):
        return await self._send_message(message=event['message'], event=event['type'])

    async def event_send_message(self, message):
        if isinstance(message['data'].get('message'), str) and len(message['data']['message']) > 0:
            msg = await self.save_message(message['data']['message'])
            return await self._group_send(
                message={
                    'message': msg.text,
                    'user': self.scope['user'].username,
                    'sent_at': msg.created_at.strftime(format='%d/%m/%Y, %H:%M'),
                }
            )
        return await self._throw_error(
            message={
                'detail': 'Invalid data',
                'valid_data_example': {
                    'message': 'Hello, chat!'
                }
            },
            event=message['event']
        )

    async def event_list_message(self, message):
        messages = await self.get_message_list()
        return await self._send_message(
            message={
                'messages': messages
            },
            event=message['event']
        )

    @creator_permission
    async def event_add_participants(self, message):
        if isinstance(message['data'].get('users'), list):
            participants = []
            for user in message['data']['users']:
                participant = await self.add_participant(user)
                if participant:
                    participants.append(participant)

            if len(participants) > 0:
                return await self._group_send(
                    message={
                        'detail': f'Users: {participants} was added to chat'
                    }
                )
        return await self._throw_error(
            message={
                'detail': 'Invalid input',
                'valid_data_example': {
                    'users': [1, 2, 3],
                }
            },
            event=message['event']
        )

    @creator_permission
    async def event_delete_participant(self, message):
        if message['data'].get('user') and message['data']['user'] != self.scope['user'].id:
            user = await self.delete_participant(message['data']['user'])
            if user:
                return await self._group_send(message={
                    'detail': f'User {user} was deleted'
                })
        return await self._throw_error(
            message={
                'detail': 'Wrong input data',
                'valid_data_example': {
                    'user': 1,
                }
            },
            event=message['event']
        )

    async def event_event_list(self, message):
        return await self._send_message(
            message={
                'available_events': [
                    'send.message',
                    'list.message',
                    'add.participants',
                    'delete.participant',
                    'event.list'
                ]
            },
            event=message['event']
        )

    @database_sync_to_async
    def get_group(self):
        try:
            return ChatRoomModel.objects.get(uuid=self.group_id)
        except:
            return

    @database_sync_to_async
    def get_creator(self):
        creator = ParticipantModel.objects.filter(group=self.group, is_creator=True).first()
        if creator:
            return creator.user
        return

    @database_sync_to_async
    def get_participants(self):
        queryset = ParticipantModel.objects.select_related('user').filter(group=self.group)
        return [i.user for i in queryset]

    @database_sync_to_async
    def get_message_list(self):
        messages = MessageModel.objects.select_related('user').filter(group=self.group).order_by('created_at')
        res = []
        for msg in messages:
            if not msg.is_viewed and msg.user != self.scope['user']:
                msg.is_viewed = True
                msg.save()

            res.append({
                'text': msg.text,
                'sender': msg.user.username,
                'sent_at': msg.created_at.strftime(format='%d/%m/%Y, %H:%M')
            })
        return res

    @database_sync_to_async
    def save_message(self, text):
        message = MessageModel.objects.create(text=text, group=self.group, user=self.scope['user'])
        return message

    @database_sync_to_async
    def add_participant(self, user_id):
        try:
            user = UserModel.objects.get(pk=user_id)
            participant, flag = ParticipantModel.objects.get_or_create(group=self.group, user=user)
            return user.username if flag else None
        except:
            return

    @database_sync_to_async
    def delete_participant(self, user_id):
        try:
            user = UserModel.objects.get(pk=user_id)
            participant = ParticipantModel.objects.get(user=user, group=self.group)
            participant.delete()
            return user.username
        except:
            return
