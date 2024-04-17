import random
import string
import os

HCLOUD_TOKEN = os.environ.get('HCLOUD_TOKEN')

if not HCLOUD_TOKEN:
    raise ValueError('HCLOUD_TOKEN missing from environment.')

def _create_random_string(size=8, choice_pool=string.ascii_letters + string.digits):
    return ''.join(random.choice(choice_pool) for _ in range(size))
