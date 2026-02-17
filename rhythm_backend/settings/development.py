"""
Development settings
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Development-specific apps
INSTALLED_APPS += [
    'django_extensions',  # Optional: useful development tools
]

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend - console output for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Disable password validators in development for easier testing
AUTH_PASSWORD_VALIDATORS = []

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
