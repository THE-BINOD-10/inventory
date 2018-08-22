from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wms_prod_10_aug',
        'USER': 'root',
        'PASSWORD': 'root',
        'TEST_MIRROR': 'default',
    }
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_local.cfg'
