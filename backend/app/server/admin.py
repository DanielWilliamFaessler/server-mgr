from django.contrib import admin

from django import forms
from django.contrib import admin
from server.server_registration import ServerTypeFactory
from server.models import (
    ExecutionMessages,
    ServerType,
    ProvisionedServerInstance,
)


class ServerTypeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        server_type_choices = [
            (str(o), str(o)) for o in ServerTypeFactory.registry
        ]
        super(ServerTypeForm, self).__init__(*args, **kwargs)
        self.fields['server_type_reference'] = forms.ChoiceField(
            choices=server_type_choices,
        )

    class Meta:
        model = ServerType
        fields = '__all__'


@admin.register(ServerType)
class ServerTypeAdmin(admin.ModelAdmin):
    form = ServerTypeForm


@admin.register(ProvisionedServerInstance)
class ServerAdmin(admin.ModelAdmin):
    actions = None
    readonly_fields = [
        'server_id',
        'server_address',
        'server_password',
        'server_name',
        'extending_lifetime_secret',
    ]
    list_display = [
        '__str__',
        'user',
        'created',
        'removal_at',
        'server_type',
        'server_id',
        'server_address',
    ]
    list_filter = [
        'user',
        'server_type',
        'created',
        'server_bears_mark_of_deletion',
    ]
    search_fields = [
        'id',
        'user__username',
        'server_type',
        'server_name',
        'server_id',
        'server_address',
    ]


@admin.register(ExecutionMessages)
class ExecutionMessagesAdmin(admin.ModelAdmin):
    list_filter = [
        'created',
        'task_name',
        'instance',
        'instance__user__username',
    ]
    search_fields = [
        'instance',
        'user_message',
        'user_trace',
        'server_type',
        'admin_message',
        'admin_trace',
    ]
