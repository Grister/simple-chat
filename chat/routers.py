from django.urls import path

from chat.consumers import MainConsumer

websocket_urlpatterns = [
    path('', MainConsumer.as_asgi(), name='ws_index'),
    # path('chat/<chat_room>/', ..., name='ws_room'),
]
