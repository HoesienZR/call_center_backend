import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'call_center_backend.settings')

app = Celery('call_center_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'check-every-6-hours': {
        'task': 'call_center.tasks.check_special_contacts',
        'schedule': crontab(hour='*/6'),  # هر ۶ ساعت یک‌بار
    },
}
