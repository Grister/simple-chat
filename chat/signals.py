from asgiref.sync import async_to_sync

from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer

from chat.models import MessageModel, ParticipantModel


def send_chat_message(chat, message):
    async_to_sync(get_channel_layer().group_send)(chat, message)


@receiver(post_save, sender=MessageModel)
def message_notice(sender, instance, created, **kwargs):
    if created:
        data = {
            'type': 'send.notification',
            'message': {
                'type': 'new message',
                'group': instance.group.name,
                'sender': instance.user.username,
                'message': instance.text,
            }
        }
        participants = ParticipantModel.objects.filter(group=instance.group).exclude(user=instance.user)

        for participant in participants:
            send_chat_message(chat=f'user_{participant.user.id}', message=data)


@receiver(post_save, sender=ParticipantModel)
def message_notice(sender, instance, created, **kwargs):
    if created and instance.group.type != 'dialog' and not instance.creator_permission:
        data = {
            'type': 'send.notification',
            'message': {
                'type': 'new group',
                'message': f'You were added to group {instance.group.name}',
            }
        }
        send_chat_message(chat=f'user_{instance.user.id}', message=data)
