from django.contrib import admin

from .models import Server

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    actions = None
    readonly_fields = [
        "server_id",
        "server_address",
        "server_password",
        'server_name',
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
    ]
    search_fields = [
        'id',
        'user__username',
        'server_type',
        'server_name',
        'server_id',
        'server_address',
    ]
