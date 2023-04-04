from django.apps import AppConfig

import importlib
import pkgutil

from icecream import ic   # type: ignore[import]

from server.server_registration import ServerTypeFactory


def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')


class ServerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'server'

    def ready(self) -> None:
        # this ensures all the providers are being registered
        import server.providers

        discovered_providers = {
            name: importlib.import_module(name)
            for _, name, _ in iter_namespace(server.providers)
        }
        ic(
            f'registered {len(discovered_providers)} providers with a total of {len(ServerTypeFactory.registry)} templates.'
        )
        ic(discovered_providers, ServerTypeFactory.registry)
        return super().ready()
