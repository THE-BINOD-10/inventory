from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'WMS_PROD1',
        'HOST': '94.130.36.188',
        'USER': 'root',
        'PASSWORD': 'Stockone@2017',
        'TEST_MIRROR': 'default',
    }
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_prod.cfg'

SERVICE_WORKER_VERSION = '0.0.1-build03.0.99'