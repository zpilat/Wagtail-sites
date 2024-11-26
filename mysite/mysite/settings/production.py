from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = ['zpilat.pythonanywhere.com']

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

try:
    from .local import *
except ImportError:
    pass
