# mypy: disable-error-code=import

import importlib
from django.contrib import admin
from django.urls import path, re_path, include

import debug_toolbar

from allauth.account.views import confirm_email, login, logout
from allauth.socialaccount import providers

providers_urlpatterns = []  # type: ignore[var-annotated]

for provider in providers.registry.get_list():
    prov_mod = importlib.import_module(provider.get_package() + '.urls')
    providers_urlpatterns += getattr(prov_mod, 'urlpatterns', [])

allauth_urls = [
    path('auth/', include(providers_urlpatterns)),
    re_path(
        r'^confirm-email/(?P<key>[-:\w]+)/',
        confirm_email,
        name='account_confirm_email',
    ),
    path('login/', login, name='account_login'),
    path('logout/', logout, name='account_logout'),
    # disable email signup by overriding the with the login url
    path('signup/', login, name='account_signup'),
]

urlpatterns = [
    path(f'admin/', admin.site.urls),
    path(f'__debug__/', include(debug_toolbar.urls)),
    path(f'accounts/', include(allauth_urls)),
    path(f'', include('core.urls')),
    path(f'servers/', include('server.urls')),
]
