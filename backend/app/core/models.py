# mypy: disable-error-code=import

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    pass

    @property
    def profile(self):
        if hasattr(self, 'profile_info'):
            return self.profile_info
        return None


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        related_name='profile_info',
        on_delete=models.CASCADE,
    )
    preferred_language = models.CharField(
        choices=settings.LANGUAGES,
        verbose_name=_('preferred language'),
        max_length=100,
    )
