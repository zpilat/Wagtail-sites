from .base import *
from decouple import config

SECRET_KEY = config('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = ['zpilat.pythonanywhere.com']

try:
    from .local import *
except ImportError:
    pass
