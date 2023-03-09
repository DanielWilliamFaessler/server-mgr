#!/usr/bin/env python3
import logging
from datetime import timedelta
import time
from django.utils import timezone
from django.conf import settings
from server_mgr.models import Server
from django.contrib.sites.models import Site


SLEEP_FOR_SECONDS = 60

logger = logging.Logger(__name__)


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


def run_info_mail_send():
    """
    renewal is only available 4 weeks before the deadline.
    """

    in_4_weeks = timezone.now() + timedelta(weeks=4)
    unsent_servers = (
        Server.objects.filter(notify_before_destroy=True)
        .filter(info_mail_sent=False)
        .filter(removal_at__lte=in_4_weeks)
    )

    if len(unsent_servers) > 0:
        try:
            site = Site.objects.get(pk=settings.SITE_ID)
        except:
            site = Site.objects.all()[0]

        url = site.domain

        if not url.startswith('http'):
            url = f'https://{url}'

        print(f'starting info mail for {url}')
        for s in unsent_servers:
            try:
                s.send_deletion_notification_mail(url)
            except Exception as e:
                logger.error(
                    f'sending email failed, continuing anyway. Error: {e}'
                )
        print('info mails sent')


def run():
    while True:
        run_cleanup()
        run_info_mail_send()
        # sleep for 1 Minute
        time.sleep(SLEEP_FOR_SECONDS)


if __name__ == '__main__':
    run()
