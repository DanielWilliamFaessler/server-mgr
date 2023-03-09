from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    CreateView,
    DeleteView,
    DetailView,
)

from .models import Server, ServerVariant
from django.contrib.auth.mixins import LoginRequiredMixin


class ServerMixin(LoginRequiredMixin):
    model = Server

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(user=self.request.user)


class ServerListView(ServerMixin, ListView):
    template_name = 'server_mgr/server_list.html'
    context_object_name = 'servers'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(user=self.request.user)


class ServerDetailView(ServerMixin, DetailView):
    template_name = 'server_mgr/server_detail.html'
    context_object_name = 'server'


class ServerCreateView(ServerMixin, CreateView):
    template_name = 'server_mgr/server_add.html'
    fields = ['server_type']

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.fields[
            'server_type'
        ].queryset = ServerVariant.get_allowed_variants(self.request.user)
        return form

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        self.object = None
        form = self.get_form()

        server_type = form.data['server_type']
        has_server_already = (
            Server.objects.filter(server_type=server_type)
            .filter(user=request.user)
            .count()
            != 0
        )
        if has_server_already:
            form.add_error(
                'server_type', 'You already have a server of this type.'
            )

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ServerDeleteView(ServerMixin, DeleteView):
    template_name = 'server_mgr/server_confirm_delete.html'
    success_url = reverse_lazy('server-list')


class ServerProlongView(ServerMixin, DeleteView):
    # FIXME: check for secret and deny access
    template_name = 'server_mgr/server_prolong.html'
    success_url = reverse_lazy('server-list')
    fields = ['server_type']

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        secret = self.kwargs['secret']
        if obj.extending_lifetime_secret != secret:
            raise Server.DoesNotExist()
        return super().get_object(*args, **kwargs)

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.prolong()
        return HttpResponseRedirect(success_url)


class ServerRestartView(ServerMixin, DeleteView):
    # A little bit cheating: we need almost everything
    # as if it would be a delete, but
    # do a reboot instead.
    template_name = 'server_mgr/server_confirm_reboot.html'
    success_url = reverse_lazy('server-list')

    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.reboot_server(self.request.user)
        return HttpResponseRedirect(success_url)
