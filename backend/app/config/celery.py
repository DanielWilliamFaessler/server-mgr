import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'run-cleanup-every-30-seconds': {
        'task': 'remove-due-servers',
        'schedule': 30.0,
        'args': (),
    },
    'send-emails-every-30-seconds': {
        'task': 'send-soon-due-mails',
        'schedule': 30.0,
        'args': (),
    },
}
