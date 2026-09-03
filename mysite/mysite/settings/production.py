from .base import *
from decouple import config

SECRET_KEY = config('DJANGO_SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = [
	"mysite-9293.rostiapp.cz",
	"pilatovic.cz",
	"www.pilatovic.cz",
]
CSRF_TRUSTED_ORIGINS = [
    "https://www.pilatovic.cz",
    "https://pilatovic.cz",
]

WAGTAILADMIN_BASE_URL = "https://www.pilatovic.cz"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
try:
    from .local import *
except ImportError:
    pass
