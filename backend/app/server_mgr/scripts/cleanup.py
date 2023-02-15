#!/usr/bin/env python3
import time
from django.utils import timezone
from server_mgr.models import Server

SLEEP_FOR_SECONDS = 60


def run_cleanup():
    print('starting cleanup')
    now = timezone.now()
    for s in Server.objects.all():
        if not s.server_id:
            s.delete()
            continue
        possible_removal_time = s.removal_at
        if possible_removal_time <= now:
            s.delete()
    print('cleanup done')


def run():
    while True:
        run_cleanup()
        # sleep for 1 Minute
        time.sleep(SLEEP_FOR_SECONDS)


if __name__ == '__main__':
    run()
