from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from chat.models import ChatRoomModel, ParticipantModel, UserModel


class BaseConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        if self.scope['user'].is_anonymous:
            await self._throw_error(message={'detail': 'Authorization failed'})
            await self.close(code=1000)
            return

    async def receive_json(self, content, **kwargs):
        message = await self.parse_content(content)
        if message:
            event = message['event'].replace('.', '_')
            return await getattr(self, f'event_{event}', self.method_undefined)(message)

        return await self._throw_error(
            message={
                'detail': 'Invalid input',
                'valid_input_example': {
                    "event": "event.example",
                    "data": {"var": "val"}
                }
            }
        )

    async def method_undefined(self, message):
        return await self._throw_error(
            message={
                'detail': 'Invalid event. You can check available events send event "event.list"'
            },
            event=message['event']
        )

    @classmethod
    async def parse_content(cls, content):
        if (isinstance(content, dict)
                and isinstance(content.get('event'), str)
                and isinstance(content.get('data'), dict)):
            return content

    async def _send_message(self, message, event=None):
        await self.send_json(content={
            'status': 'ok',
            'event': event,
            'message': message
        })

    async def _throw_error(self, message, event=None):
        await self.send_json(content={
            'status': 'error',
            'event': event,
            'message': message
        })


class MainConsumer(BaseConsumer):
    async def connect(self):
        await super().connect()
        self.channel = f'user_{self.scope['user'].id}'
        await self.channel_layer.group_add(self.channel, self.channel_name)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.channel, self.channel_name)
        return await super().disconnect(code)

    async def send_notification(self, event):
        return await self._send_message(message=event['message'], event=event['type'])

    async def event_group_create(self, massage):
        if (isinstance(massage['data'].get('name'), str)
                and isinstance(massage['data'].get('participants'), list)
                and isinstance(massage['data'].get('type'), str)):
            group = await self.create_group(
                name=massage['data']['name'],
                participants=massage['data']['participants'],
                chat_type=massage['data']['type']
            )
            if group:
                return await self._send_message(
                    message={'detail': f'Group {group.name} was created'},
                    event=massage['event']
                )

        return await self._throw_error(message={
            'detail': 'Invalid data',
            'valid_data_example': {
                'name': 'your_group_name',
                'participants': [1, 2, 3],
                'type': 'group'
            }
        })

    async def event_event_list(self, message):
        return await self._send_message(
            message={
                'available_events': [
                    'group.create',
                    'group.list',
                    'group.delete',
                    'user.list',
                    'event.list'
                ]
            },
            event=message['event']
        )

    async def event_group_list(self, message):
        return await self._send_message(
            message=await self.group_list(self.scope['user']),
            event=message['event']
        )

    async def event_user_list(self, message):
        return await self._send_message(
            message=await self.user_list(),
            event=message['event']
        )

    async def event_group_delete(self, message):
        if isinstance(message['data'].get('group'), str):
            group = message['data']['group']
            available_groups = {
                group['group_name']: group['group_uuid']
                for group in await self.group_list(self.scope['user'])
                if group['is_creator']
            }

            if group in available_groups.keys():
                await self.delete_group(available_groups[group])
                return await self._send_message(
                    message={
                        'detail': f'Group {group} was deleted'
                    },
                    event=message['event']
                )

        return await self._throw_error(message={
            'detail': 'Invalid data',
            'valid_data_example': {
                'group': 'GroupName',
            }
        })

    @database_sync_to_async
    def add_participant(self, group, user):
        participant = ParticipantModel(user=user, group=group)
        participant.save()

    @database_sync_to_async
    def create_group(self, name, participants, chat_type):
        if (chat_type not in ChatRoomModel.TYPES or
                (chat_type == 'dialog' and len(participants) > 1)):
            return
        group = ChatRoomModel.objects.create(name=name, type=chat_type)

        ParticipantModel.objects.create(group=group, user=self.scope['user'], is_creator=True)
        for participant in participants:
            user = UserModel.objects.filter(pk=participant).first()
            if user:
                ParticipantModel.objects.get_or_create(group=group, user=user)

        return group

    @database_sync_to_async
    def delete_group(self, group_uuid):
        group = ChatRoomModel.objects.get(pk=group_uuid)
        group.delete()

    @database_sync_to_async
    def group_list(self, user):
        data = []
        chats = user.chats.all().select_related("group")
        for chat in chats:
            data.append({
                "group_uuid": str(chat.group.uuid),
                "group_name": chat.group.name,
                "group_link": chat.group.link,
                "is_creator": chat.is_creator
            })
        return data

    @database_sync_to_async
    def user_list(self):
        users = UserModel.objects.all().exclude(pk=self.scope['user'].id)
        return [{'id': user.id, 'username': user.username} for user in users]
