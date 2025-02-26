from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stockone',
        'HOST': 'localhost',
        'USER': 'stockone',
        'PASSWORD': 'Stockone@1234',
        'TEST_MIRROR': 'default'
    },
    'reversion': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stockone',
        'USER': 'stockone',
        'HOST': 'localhost',
        'PASSWORD': 'Stockone@1234',
        'TEST_MIRROR': 'default'
    },
    'reports': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'stockone',
        'USER': 'stockone',
        'HOST': 'localhost',
        'PASSWORD': 'Stockone@1234',
        'TEST_MIRROR': 'reports',
    } 
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_prod.cfg'

SERVICE_WORKER_VERSION = '0.0.1-build03.0.99'
