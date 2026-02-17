"""
Celery configuration for rhythm_backend project.
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from decouple import config

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rhythm_backend.settings.development')

app = Celery('rhythm_backend')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    broker_url=config('REDIS_URL', default='redis://localhost:6379/0'),
    result_backend=config('REDIS_URL', default='redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
