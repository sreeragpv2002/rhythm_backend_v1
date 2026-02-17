"""
ASGI config for rhythm_backend project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rhythm_backend.settings.development')

application = get_asgi_application()
