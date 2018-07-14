from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stockonenew',
        'USER': 'root',
        'PASSWORD': 'root',
        'TEST_MIRROR': 'default'
	
    }
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_local.cfg'
