import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'call_center_backend.settings')

app = Celery('call_center_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()