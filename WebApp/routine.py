from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import url
from django_eel.consumers import EelConsumer

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    "websocket": URLRouter([
        url(r"^eel$", EelConsumer), # do not alter this line
    ]),
})
