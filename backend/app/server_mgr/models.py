from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.db import models
from django.template import Context, Template
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from django.utils import timezone

from django_extensions.db.models import TimeStampedModel
from server_mgr.providers.hetzner import (
    ServerInfo,
    destroy,
    reboot,
    reset_pw,
    status,
)

User = get_user_model()


class ServerVariant(models.Model):
    type_id = models.CharField(
        max_length=40, help_text='ensure text is spaces free'
    )
    name = models.CharField(max_length=250, help_text='user facing text')
    instance_type = models.CharField(max_length=10)
    image_name = models.CharField(
        max_length=250,
        help_text='snapshots do not have a name, only a description. ensure the description (ie. `superset`) is unique in the corresponding project space. this image (snapshot) needs to exist on the hetzner server, else this action fails.',
    )
    location = models.CharField(
        max_length=20,
        default='nbg1',
        help_text='the location must be the same as the location of the snapshot.',
    )
    description = models.CharField(max_length=250, null=True, blank=True)
    setup_reference = models.URLField(
        max_length=250,
        default='https://gitlab.ost.ch/ifs/infrastructure/setup_scripts',
    )
    user_message = models.TextField(null=True, blank=True)
    remove_after_minutes = models.IntegerField(
        default=4 * 60, help_text='default is 4h.'
    )

    def __str__(self) -> str:
        return self.name

    def create_server(self, username: str):
        from .providers.hetzner import create_hetzner_server

        labels = {'username': username}
        return create_hetzner_server(self, labels)

    @classmethod
    def _create_default_server(cls):
        cls(
            type_id='superset',
            name='Superset (Hetzner)',
            instance_type='cx21',
            location='nbg1',
            # this image (snaphsot) needs to exist on the
            # hetzner server, else this action fails.
            image_name='superset',
            description='Superset Instance, running on Hetzner',
            # the next setting isn't used, setup and script would need to be adapted.
            # most likely it is a better idea to use terraform or pulumi for this.
            # but like this, we at least know where to look for the setup script
            setup_reference='https://gitlab.ost.ch/ifs/infrastructure/setup_scripts/-/raw/main/superset/setup.sh',
            #
            user_message="""Your instance should soon (usually within 3 minutes) be available at 
<a target="_blank" href="http://{{ server.server_address }}:8088">http://{{ server.server_address }}:8088</a>.
It will be active until {{ server.removal_at|date:"H:i:s (d-m-y)" }} and then destroyed (including your data!).<br />
You can login using the standard username <code>admin</code> and password <code>admin</code>.
Your Server credentials can be found under details.<br />""",
            remove_after_minutes=4 * 60,
        ).save()


class Server(TimeStampedModel, models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    usage = models.TextField(null=False, default='', blank=True)
    server_type = models.ForeignKey(
        'server_mgr.ServerVariant',
        on_delete=models.CASCADE,
    )
    user_message = models.TextField(null=True, blank=True)
    removal_at = models.DateTimeField(null=False, blank=False)

    # these fields are being added later
    server_id = models.CharField(null=False, blank=False, max_length=255)
    server_name = models.CharField(
        null=False, blank=False, max_length=255, default=''
    )
    server_address = models.URLField(null=True, blank=True)
    server_user = models.CharField(max_length=200, null=True, blank=True)
    # this needs to be plain text, to be able to display again
    server_password = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self) -> str:
        name = f'{self.user.username}: {self.server_type}'
        return name

    def _has_destroy_perms(self, user: User):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.user == user

    def _has_change_perms(self, user: User):
        return self._has_destroy_perms(user)

    def _has_creation_perms(self, server_type):
        if not self.user.is_authenticated:
            return False
        if self.user.is_superuser:
            return True
        return (
            Server.objects.filter(server_type=server_type)
            .filter(user=self.user)
            .count()
            == 0
        )

    def provision_server(self):
        if self._has_creation_perms(self.server_type):
            info = self.server_type.create_server(self.user.username)
            return info
        raise PermissionError(
            'You lack the permissions to create a server or there is already one.'
        )

    def reboot_server(self, user: User):
        if self._has_change_perms(user):
            reboot(self.server_id)

    def reset_pw(self, user: User):
        if self._has_change_perms(user):
            new_pw = reset_pw(self.server_id)
            self.server_password = new_pw
            self.save()

    def get_server_status(self, user: User):
        if self._has_change_perms(user):
            return status(self.server_id)

    def destroy_server(self, user: User):
        if self._has_destroy_perms(user):
            self.delete()

    def get_absolute_url(self):
        return reverse_lazy('server-list')
        # return reverse_lazy('server-details', args=[self.id])

    def get_full_server_type(self, server_type):
        return self.server_type

    def save(self, **kwargs):
        if not self.server_id:
            s = self.provision_server()
            assert s is not None
            self.user = self.user
            self.usage = self.server_type
            self.server_id = s.id
            self.server_address = s.address
            self.server_user = s.username
            self.server_password = s.password
            self.server_name = s.name

            # extra stuff, like template
            remove_after_minutes = self.server_type.remove_after_minutes
            self.removal_at = timezone.now() + timedelta(
                minutes=remove_after_minutes
            )
            t = Template(self.server_type.user_message)
            self.user_message = t.render(context=Context(dict(server=self)))
        return super().save(**kwargs)

    def delete(self, *args, **kwargs):
        destroy(self.server_id)
        return super().delete(*args, **kwargs)
