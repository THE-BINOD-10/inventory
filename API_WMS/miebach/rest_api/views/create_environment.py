import os
import django


class Environment:
    def __init__(self):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
        django.setup()


Environment()
