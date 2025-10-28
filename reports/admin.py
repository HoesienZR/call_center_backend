from django.contrib import admin

from .models import *


# Register your models here.


@admin.register(CallStatistics)
class CallStatisticsAdmin(admin.ModelAdmin):
    list_display = ('contact', 'project', 'total_calls', 'successful_calls', 'response_rate', 'last_call_date')
    readonly_fields = ('updated_at',)
