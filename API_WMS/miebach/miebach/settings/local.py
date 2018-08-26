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

ONESIGNAL_AUTH_KEY = 'MGUwNmIwOWEtNWY4ZS00NTYzLWE0NmYtOTA5OTY3N2ExYzg0'
ONESIGNAL_APP_ID = '98737db9-a2c9-4ff7-be74-42149f21679f'  #SM_NEW_PUSH

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_local.cfg'
