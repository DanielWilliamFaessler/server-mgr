from django.urls import path

from .views import (
    ServerListView,
    ServerDetailView,
    ServerCreateView,
    ServerDeleteView,
)

urlpatterns = [
    path('servers/', ServerListView.as_view(), name='server-list'),
    path('servers/add/', ServerCreateView.as_view(), name='server-add'),
    path(
        'servers/<int:pk>/', ServerDetailView.as_view(), name='server-details',
    ),
    path(
        'servers/<int:pk>/delete/',
        ServerDeleteView.as_view(),
        name='server-delete',
    ),
]
