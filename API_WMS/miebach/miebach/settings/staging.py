from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'STAGING',
        'USER': 'root',
        'PASSWORD': '0510^2017',
        'TEST_MIRROR': 'default',
    }
}


INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_staging.cfg'

SERVICE_WORKER_VERSION = '0.0.1-build03.0.99'