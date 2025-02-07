import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from chat.routers import websocket_urlpatterns
from chat.middlewares import TokenAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': TokenAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
})
