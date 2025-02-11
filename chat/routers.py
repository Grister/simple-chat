from django.urls import path, re_path

from chat.consumers import MainConsumer, ChatRoomConsumer


websocket_urlpatterns = [
    path('', MainConsumer.as_asgi(), name='ws_index'),
    path('chat/<chat_room>/', ChatRoomConsumer.as_asgi(), name='ws_room'),
]
