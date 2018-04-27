from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'WMS_DEV',
        'USER': 'root',
        'PASSWORD': '123',
        'TEST_MIRROR': 'default',
    }
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_local.cfg'
