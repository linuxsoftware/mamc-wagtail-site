from .base import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

#TEMPLATE_DEBUG = True
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'




try:
    from .local import *
except ImportError:
    pass
