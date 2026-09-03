from .base import *
from decouple import config

SECRET_KEY = config('DJANGO_SECRET_KEY')

DEBUG = False

# Environment-specific values are defined in the untracked local.py file.
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []

try:
    from .local import *
except ImportError:
    pass
