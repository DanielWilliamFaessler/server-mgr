# mypy: disable-error-code=import
import random

from dataclasses import asdict

from user_messages import api

from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.generic.base import TemplateView, RedirectView
from django.conf import settings

from core.serializers import MessageSerializer


class HomePageView(TemplateView, RedirectView):
    template_name = 'core/home.html'

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            url = reverse('server:server-list')
            return HttpResponseRedirect(url)
        return super().get(request, *args, **kwargs)


def user_messages(request, *args, **kwargs):
    # messages limited to the user on the request (and [] if not authenticated)
    messages = api.get_messages(request=request)

    if settings.DEBUG:
        if request.user.is_authenticated:
            api.debug(
                request.user,
                'Oww - not a real oww though',
                meta={
                    'url': 'This is only a debug message when DEBUG=True',
                },
            )
    msgs = [
        asdict(
            MessageSerializer(
                content=msg.message,
                id=msg.id,
                tags=msg.tags,
                meta=msg.meta,
                level_tag=msg.level_tag,
            )
        )
        for msg in messages
    ]
    return JsonResponse(msgs, safe=False)


class MessagesView(TemplateView):
    template_name = 'core/display_messages_snippet.html'

    def get_context_data(self, **kwargs):
        if settings.DEBUG and settings.ENABLE_USER_MESSAGES_RANDOM_DEBUG:
            if self.request.user.is_authenticated:
                if random.choice([True, False, False, False, False, False]):
                    api.debug(
                        self.request.user,
                        'DEVELOPMENT DEBUG TEST MESSAGE: Oww - not a real oww though',
                        meta={
                            'url': 'This is only a debug message when DEBUG=True',
                        },
                    )
        context = super().get_context_data(**kwargs)
        context['messages'] = api.get_messages(request=self.request)
        return context
