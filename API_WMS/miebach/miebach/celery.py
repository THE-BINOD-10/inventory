from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab
from kombu import Queue
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miebach.settings')

app = Celery('miebach',
            #  broker='redis://', include=['rest_api.views.customscriptdontpushtogit'])
            broker='redis://', include=[ 'stockone_integrations.automate' ,'rest_api.views.customscriptdontpushtogit'])
             #include=['stockone_integrations.automate', 'rest_api.views.customscriptdontpushtogit'])


#app.config_from_object('django.conf:settings', namespace='CELERY')
#app.conf.timezone = 'Asia/Kolkata'

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'Asia/Kolkata'
app.conf.CELERYBEAT_SCHEDULE = {
    'integrate_data': {
            'task': 'stockone_integrations.automate.runStoredAutomatedTasks',
            'schedule': crontab(minute='*/60'),
             #'schedule': crontab(minute='*/5'),
            'args': None
    },
}
app.conf.task_default_queue = 'default'
app.conf.task_queues = (
    Queue('queueA',    routing_key='tasks.task_1'),
    Queue('queueB',    routing_key='tasks.task_2'),
)
#app.conf.CELERYBEAT_SCHEDULE = {
#    'integrate_data': {
#        'task': 'stockone_integrations.automate.runStoredAutomatedTasks',
        #'schedule': crontab(minute='*/5'),
#        'schedule': crontab(hour='*/1'),
#        'args': None
#    },
#}

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
