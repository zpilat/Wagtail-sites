import os

ENV = os.getenv('DJANGO_ENV', 'dev')

if ENV == 'production':
    from .production import *
else:
    from .dev import *
