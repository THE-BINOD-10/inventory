from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'STAGING',
        'USER': 'root',
        'PASSWORD': 'krothapalli',
        'TEST_MIRROR': 'default'
    }
}

ONESIGNAL_AUTH_KEY = 'YTc3ZGRiZjctZDZkZS00ZGMyLWFhZmMtOTUyNzdhMDJiOGUx'
ONESIGNAL_APP_ID = '98737db9-a2c9-4ff7-be74-42149f21679f'  #SM_NEW_PUSH

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_local.cfg'
