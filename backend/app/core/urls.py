from django.urls import path

from .views import (
    HomePageView,
    MessagesView,
    user_messages,
)

# this is for reversing the urls (ie. "server:server-list")
app_name = 'core'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('msgs/', MessagesView.as_view(), name='user-messages-snippet'),
    #  if json variant shoiuld be neded:
    # path('usermessages/', user_messages, name='get-user-messages'),
]
