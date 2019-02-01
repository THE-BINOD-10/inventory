"""
Django settings for miebach project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+vd3a4(t9482@n$q(*2d#qsaqmd2ttgi)2sfn558(lo_a12nf8'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

#TEMPLATE_DEBUG = True

MAINTENANCE_MODE = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    #'grappelli',
    'admin_view_permission',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'miebach_admin',
    #'maintenancemode',
    'api_calls',
    'rest_api',
    'oauth2_provider',
    'reversion'
)

#INSTALLED_APPS = ("longerusername",) + INSTALLED_APPS
'''
AUTHENTICATION_BACKENDS = (
'oauth2_provider.backends.OAuth2Backend',
)
'''
MIDDLEWARE_CLASSES = (
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    #'reversion.middleware.RevisionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
)
'''
MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'maintenancemode.middleware.MaintenanceModeMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]
'''

ROOT_URLCONF = 'miebach.urls'

WSGI_APPLICATION = 'miebach.wsgi.application'

TEMPLATES = [
{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [os.path.join(BASE_DIR, 'miebach_admin')],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]
'''
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'miebach_admin'),
    os.path.join(BASE_DIR, 'static', 'css'),
)
'''
#STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'static'),
)

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

#Accepting More Fields through request
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

#Accepting More Size request Object
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760

GRAPPELLI_ADMIN_TITLE = 'MIEBACH Admin'

# SECURE_SSL_REDIRECT = True

# SESSION_COOKIE_SECURE = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = ''

LOGIN_URL = '/login/'

CORS_ORIGIN_ALLOW_ALL = True

CORS_EXPOSE_HEADERS = (
    'Access-Control-Allow-Origin: *',
)

CORS_ALLOW_CREDENTIALS = True

# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt' : '%d/%b/%Y %H:%M:%S'
        },
        'simple': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt' : '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'info_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'filename': 'logs/miebach_info.log',
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        },
        "warning_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "formatter": "simple",
            "filename": "logs/miebach_warning.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        },
        "django_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "verbose",
            "filename": "logs/django_info.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        }
    },
    'loggers': {
        'django': {
            'handlers':['django_file_handler'],
            'propagate': True,
            'level':'DEBUG',
        },
        'miebach_admin': {
            'handlers': ['info_file_handler', 'warning_file_handler'],
            'level': 'INFO',
        },
    }
}

AUTHORIZATION_CODE_EXPIRE_SECONDS=600
BARCODE_DEFAULT = {
		'format_type': 1,
                'size': (60,25),
                'show_fields': ['SKUCode', 'Product', ['Size', 'Gender', 'Qty', 'Color'], ['Phone', 'Email']], #Give nested list if u need multiple columns in same line
                'rows_columns' : (1,1),
                'styles' : {'leftIndent': 4, 'spaceAfter': 4, 'spaceBefore': 4, 'fontName': 'Arial', 'fontSize': 6, 'spaceShrinkage': 12, 'leading': 9, 'showBoundary': 0.1, 'rightIndent': 0},
		}
