from django.contrib import admin
from django.urls import path, include

import debug_toolbar

urlpatterns = [
    path(f'admin/', admin.site.urls),
    path(f'__debug__/', include(debug_toolbar.urls)),
    path(f'accounts/', include('allauth.urls')),
    path(f'', include('core.urls')),
]
