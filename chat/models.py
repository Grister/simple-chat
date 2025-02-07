import uuid
from django.db import models
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class ChatRoomModel(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)

    def __str__(self):
        return self.name

    @property
    def link(self):
        return f"chat/{self.uuid}"


class ParticipantModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='chats')
    group = models.ForeignKey(ChatRoomModel, on_delete=models.CASCADE, related_name='participants')

    def __str__(self):
        return f'{self.user} -- {self.group}'


class MessageModel(models.Model):
    text = models.TextField()
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='messages')
    group = models.ForeignKey(ChatRoomModel, on_delete=models.CASCADE, related_name='messages')
    is_viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'<{self.text[:20]}> from {self.user} in {self.group}'
