from dataclasses import dataclass
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

from server_mgr.providers.hetzner import (
    create_superset_server,
    destroy,
    reboot,
    reset_pw,
    status,
)

User = get_user_model()


@dataclass
class ServerType:
    id: str
    name: str
    description: str = None
    # See here: https://gitlab.ost.ch/ifs/infrastructure/setup_scripts
    # for an example howto maybe use this in the future
    setup_script_url: str = None


server_types = [
    ServerType(
        id='superset',
        name='Superset (Hetzner)',
        # this image (snaphsot) needs to exist on the
        # hetzner server, else this action fails.
        image_name='superset-setup',
        description='Superset Instance, running on Hetzner',
        # this doesn't run through, script would need to be adapted.
        # most likely it is a better idea to use terraform or pulumi for this.
        # setup_script_url='https://gitlab.ost.ch/ifs/infrastructure/setup_scripts/-/raw/main/superset/setup.sh',
    )
]


class Server(models.Model):
    SERVER_TYPE_SUPERSET = 'superset'
    SERVER_TYPE_CHOICES = [(st.id, st.name) for st in server_types]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    usage = models.TextField(null=False, default='', blank=True)
    server_type = models.CharField(
        max_length=40,
        choices=SERVER_TYPE_CHOICES,
    )
    # these fields are being added later
    server_id = models.CharField(null=False, blank=False, max_length=255)
    address = models.URLField(null=True, blank=True)
    server_user = models.CharField(max_length=200, null=True, blank=True)
    # this needs to be plain text, to be able to display again
    server_password = models.CharField(max_length=200, null=True, blank=True)

    def _has_destroy_perms(self, user: User):
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return self.user == user

    def _has_change_perms(self, user: User):
        return self._has_destroy_perms(user)

    def _has_creation_perms(self, user: User):
        if self._has_change_perms(user):
            return (
                Server.objects.filter(server_type=self.server_type)
                .filter(user=self.user)
                .count()
                == 0
            )
        return False

    def provision_server(self, user: User):
        if self._has_creation_perms(user):
            if self.server_id is None:
                info = create_superset_server(user)
                self.server_id = info.server_id

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
            destroy(self.server_id)
            self.server_id = None
            self.address = None
            self.server_user = None
            self.server_password = None
            self.save()
