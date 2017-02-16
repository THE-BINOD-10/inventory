import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

import json
import requests
import traceback

from urlparse import urlparse, urljoin, urlunparse, parse_qs
from dateutil import parser

from rest_api.views.retailone import _pull_market_data
from miebach_admin.models import *


def sync_orders(user):
    print 'calling sync_orders for user_id: ', user.id
    _pull_market_data(user, '', '')

def get_users():
    user_ids = Integrations.objects.filter(name='retailone', status=1).values_list('user', flat=True).distinct()
    users = User.objects.filter(id__in=user_ids)

    return users

def main():
    users = get_users()

    for user in users:
        sync_orders(user)

if __name__ == '__main__':
    main()
