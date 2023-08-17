from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/list/(?P<user_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/message/(?P<room_id>\w+)/(?P<user>\w+)/$', consumers.ChatMessage.as_asgi()),
]