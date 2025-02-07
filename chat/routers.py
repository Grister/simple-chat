from django.urls import path

websocket_urlpatterns = [
    path('', ..., name='ws_index'),
    path('chat/<chat_room>/', ..., name='ws_room'),
]
