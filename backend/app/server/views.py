from django.contrib.messages import constants as message_constants
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    DeleteView,
    DetailView,
)
from django.contrib.auth.mixins import LoginRequiredMixin

from user_messages import api   # type: ignore[import]

from server.tasks import (
    create_server,
    delete_server,
    prolong_server,
    pw_reset_server,
    reboot_server,
    start_server,
    stop_server,
)
from server.models import ServerType, ProvisionedServerInstance


class ServerMixin(LoginRequiredMixin):   # type: ignore[misc]
    model = ProvisionedServerInstance

    def get_queryset(self):
        qs = super().get_queryset().filter(server_bears_mark_of_deletion=False)
        if self.request.user.is_superuser:
            return qs
        return qs.filter(user=self.request.user)


class ServerListView(ServerMixin, ListView):   # type: ignore[misc]
    template_name = 'server/server_list.html'
    context_object_name = 'servers'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs.order_by('user')
        return qs.filter(user=self.request.user)


class ServerDetailView(ServerMixin, DetailView):   # type: ignore[misc]
    template_name = 'server/server_detail.html'
    context_object_name = 'server'


class ServerCreateView(ServerMixin, CreateView):   # type: ignore[misc]
    template_name = 'server/server_add.html'
    fields = ['server_type']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields[
            'server_type'
        ].queryset = ServerType.get_user_choosable_option(self.request.user)
        return form

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        form.instance.user = self.request.user
        self.object = form.save()
        api.add_message(
            user=self.request.user,
            level=message_constants.INFO,
            message='Server is being created. Please wait a few minutes.',
        )
        return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        self.object = None
        form = self.get_form()

        server_type = form.data['server_type']
        has_server_already = (
            ProvisionedServerInstance._user_has_instance_already(
                server_type, request.user
            )
        )

        if has_server_already:
            form.add_error(
                'server_type', 'You already have a server of this type.'
            )

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ServerDeleteView(ServerMixin, DeleteView):   # type: ignore[misc]
    template_name = 'server/server_confirm_delete.html'
    success_url = reverse_lazy('server:server-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.server_bears_mark_of_deletion = True
        self.save()
        api.add_message(
            user=request.user,
            level=message_constants.INFO,
            message='Server marked for deletion.',
        )
        delete_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(self.get_success_url())


class ServerProlongView(ServerMixin, DeleteView):   # type: ignore[misc]
    # FIXME: check for secret and deny access
    template_name = 'server/server_prolong.html'
    success_url = reverse_lazy('server:server-list')
    fields = ['server_type']

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        secret = self.kwargs['secret']
        if obj.extending_lifetime_secret != secret:
            raise ProvisionedServerInstance.DoesNotExist()
        return super().get_object(*args, **kwargs)

    def form_valid(self, form):
        success_url = reverse(
            'server:server-details', kwargs=dict(pk=self.object.id)
        )
        prolong_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(success_url)


class ServerRestartView(ServerMixin, DeleteView):   # type: ignore[misc]
    # A little bit cheating: we need almost everything
    # as if it would be a delete, but
    # do a reboot instead.
    template_name = 'server/server_confirm_reboot.html'

    def form_valid(self, form):
        success_url = reverse(
            'server:server-details', kwargs=dict(pk=self.object.id)
        )
        reboot_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(success_url)


class ServerStopView(ServerMixin, DeleteView):   # type: ignore[misc]
    # A little bit cheating: we need almost everything
    # as if it would be a delete, but
    # do a reboot instead.
    template_name = 'server/server_confirm_stop.html'

    def form_valid(self, form):
        success_url = reverse(
            'server:server-details', kwargs=dict(pk=self.object.id)
        )
        stop_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(success_url)


class ServerStartView(ServerMixin, DeleteView):   # type: ignore[misc]
    # A little bit cheating: we need almost everything
    # as if it would be a delete, but
    # do a reboot instead.
    template_name = 'server/server_confirm_start.html'

    def form_valid(self, form):
        success_url = reverse(
            'server:server-details', kwargs=dict(pk=self.object.id)
        )
        start_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(success_url)


class ServerPWResetViewView(ServerMixin, DeleteView):   # type: ignore[misc]
    # A little bit cheating: we need almost everything
    # as if it would be a delete, but
    # do a reboot instead.
    template_name = 'server/server_confirm_pw_reset.html'

    def form_valid(self, form):
        success_url = reverse(
            'server:server-details', kwargs=dict(pk=self.object.id)
        )
        pw_reset_server.delay(instance_id=self.object.id)
        return HttpResponseRedirect(success_url)
