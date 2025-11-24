from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()

class Ticket(models.Model):
    user =  models.ForeignKey(User,related_name="tickets",on_delete=models.CASCADE,verbose_name='سازنده')
    title = models.CharField(max_length=32,verbose_name="عنوان")
    description = models.TextField(verbose_name="متن")
    done = models.BooleanField(default=False,verbose_name="انجام شده ")
    created_at = models.DateField(auto_now=True,verbose_name="ساخته شده")
    class Meta:
        verbose_name = 'تیکت'
        verbose_name_plural = "تیکت ها "
        ordering = ['-created_at']
    def __str__(self):
        return self.title
