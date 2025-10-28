from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class CustomUser(AbstractUser):
    """
    مدل کاربر سفارشی که شماره موبایل و اجازه ساخت پروژه را نیز شامل می‌شود.
    """
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="شماره موبایل",)
    can_create_projects = models.BooleanField(default=False, verbose_name="می‌تواند پروژه بسازد")
    def __str__(self):
        return self.username
