from django.contrib import admin
from chat.models import ChatRoomModel, ParticipantModel, MessageModel


@admin.register(ChatRoomModel)
class ChatRoomAdmin(admin.ModelAdmin):
    pass


@admin.register(ParticipantModel)
class ParticipantAdmin(admin.ModelAdmin):
    pass


@admin.register(MessageModel)
class MessageAdmin(admin.ModelAdmin):
    pass
