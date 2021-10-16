from .base import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'METROPOLIS_PROD',
        'USER': 'root',
        'PASSWORD': 'stockonedev@2020',
        'TEST_MIRROR': 'default'
    },
    'reversion': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'METROPOLIS_PROD_REVERSION',
        'USER': 'root',
        'PASSWORD': 'stockonedev@2020',
        'TEST_MIRROR': 'default'
    },
    'reports': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'METROPOLIS_PROD',
        'USER': 'metropolis_reports',
        'PASSWORD': 'Stockone^2021',
        'HOST': '65.21.93.111',
        'TEST_MIRROR': 'reports',
    } 
}

INTEGRATIONS_CFG_FILE = 'rest_api/views/configuration_prod.cfg'

SERVICE_WORKER_VERSION = '0.0.1-build03.0.99'
