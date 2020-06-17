from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miebach.settings')

app = Celery('miebach',
             broker='redis://',
             include=['stockone_integrations.automate'])


app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'Asia/Kolkata'

app.conf.CELERYBEAT_SCHEDULE = {
    'integrate_data': {
        'task': 'stockone_integrations.automate.runStoredAutomatedTasks',
        'schedule': crontab(minute=01, hour=15),
        'args': None
    },
}

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
