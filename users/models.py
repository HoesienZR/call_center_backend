from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="شماره موبایل")
    can_create_projects = models.BooleanField(default=False, verbose_name="می‌تواند پروژه بسازد")

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.phone_number
