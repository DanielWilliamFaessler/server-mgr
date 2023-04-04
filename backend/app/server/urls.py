from django.urls import include, path

from .views import (
    ServerListView,
    ServerDetailView,
    ServerCreateView,
    ServerDeleteView,
    ServerPWResetViewView,
    ServerRestartView,
    ServerProlongView,
    ServerStopView,
    ServerStartView,
)

# this is for reversing the urls (ie. "server:server-list")
app_name = 'server'

urlpatterns = [
    path('', ServerListView.as_view(), name='server-list'),
    path('add/', ServerCreateView.as_view(), name='server-add'),
    path(
        '<int:pk>/',
        ServerDetailView.as_view(),
        name='server-details',
    ),
    path(
        '<int:pk>/delete/',
        ServerDeleteView.as_view(),
        name='server-delete',
    ),
    path(
        '<int:pk>/reboot/',
        ServerRestartView.as_view(),
        name='server-reboot',
    ),
    path(
        '<int:pk>/start/',
        ServerStartView.as_view(),
        name='server-start',
    ),
    path(
        '<int:pk>/stop/',
        ServerStopView.as_view(),
        name='server-stop',
    ),
    path(
        '<int:pk>/pwreset/',
        ServerPWResetViewView.as_view(),
        name='server-pw-reset',
    ),
    path(
        '<int:pk>/prolong/<uuid:secret>/',
        ServerProlongView.as_view(),
        name='server-prolong',
    ),
    path(
        'celery-progress/',
        include('celery_progress.urls', namespace='celery-progress'),
    ),
]
