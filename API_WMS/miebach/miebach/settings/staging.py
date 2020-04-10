from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'STAGING',
        'USER': 'root',
        'HOST': '78.46.82.139',
        'PASSWORD': 'stockonedb@2019',
        'TEST_MIRROR': 'default',
    },
      'reversion': {
          'ENGINE': 'django.db.backends.mysql',
          'NAME': 'STAGING_REVERSION',
          'USER': 'root',
          'HOST': '78.46.82.139',
          'PASSWORD': 'stockonedb@2019',
      }

}

ONESIGNAL_AUTH_KEY = 'NThmMDIxOTQtYWE4Yi00ZDdmLThjYzEtNGRiMDJhNjkwNTAw'
ONESIGNAL_APP_ID = '8afefefe-2640-461c-8c3a-ca744702d33e'
INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_staging.cfg'

SERVICE_WORKER_VERSION = '0.0.1-build03.0.171'
