# Generated by Django 4.1.7 on 2023-02-15 14:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server_mgr', '0006_server_server_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='server',
            old_name='user_massage',
            new_name='user_message',
        ),
    ]
