from .base import *

# Import environment-specific settings
import os
from decouple import config

env = config('DJANGO_ENV', default='development')

if env == 'production':
    from .production import *
else:
    from .development import *
