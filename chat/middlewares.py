from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.auth import AuthMiddlewareStack


@database_sync_to_async
def get_user_by_token(token):
    try:
        instance = Token.objects.get(key=token)
        return instance.user
    except Token.DoesNotExist:
        return AnonymousUser


class CheckValidPath:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        try:
            return await self.inner(scope, receive, send)
        except ValueError:
            await send({
                'type': 'websocket.close',
                'code': 1000,
                'detail': 'Invalid route'
            })
            return


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            try:
                prefix, token = headers[b'authorization'].decode().split()
                if prefix == 'Token':
                    scope['user'] = await get_user_by_token(token)
            except ValueError:
                pass
        return await self.inner(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))

def CheckValidPathStack(inner):
    return CheckValidPath(TokenAuthMiddlewareStack(inner))
