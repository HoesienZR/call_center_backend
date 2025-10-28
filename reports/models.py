from django.db import models
from django.conf import settings

# Create your models here.

class CachedStatistics(models.Model):
    """مدل برای کش آمار"""
    stat_type = models.CharField(max_length=50, verbose_name="نوع آمار")
    stat_key = models.CharField(max_length=100, verbose_name="کلید آمار")
    stat_value = models.TextField(verbose_name="مقدار آمار")
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name="محاسبه شده در")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="انقضا در")

    class Meta:
        verbose_name = "آمار کش شده"
        verbose_name_plural = "آمارهای کش شده"
        unique_together = ['stat_type', 'stat_key']
        ordering = ['-calculated_at']

    def __str__(self):
        return f"{self.stat_type} - {self.stat_key}"

    def get_stat_value(self):
        """دریافت مقدار آمار به صورت dict"""
        if self.stat_value:
            try:
                return json.loads(self.stat_value)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_stat_value(self, value_dict):
        """تنظیم مقدار آمار"""
        if value_dict:
            self.stat_value = json.dumps(value_dict, ensure_ascii=False)
        else:
            self.stat_value = '{}'

    def is_expired(self):
        """بررسی انقضای کش"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    @classmethod
    def get_cached_stat(cls, stat_type, stat_key):
        """دریافت آمار کش شده"""
        try:
            cached = cls.objects.get(stat_type=stat_type, stat_key=stat_key)
            if not cached.is_expired():
                return cached.get_stat_value()
        except cls.DoesNotExist:
            pass
        return None

    @classmethod
    def set_cached_stat(cls, stat_type, stat_key, value_dict, expires_in_hours=24):
        """تنظیم آمار کش شده"""
        cached, created = cls.objects.get_or_create(
            stat_type=stat_type,
            stat_key=stat_key
        )

        cached.set_stat_value(value_dict)
        cached.calculated_at = datetime.now()
        cached.expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        cached.save()

        return cached


class CallStatistics(models.Model):
    """مدل برای آمار تماس‌ها"""
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='call_statistics', verbose_name="مخاطب")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='call_statistics', verbose_name="پروژه")
    total_calls = models.PositiveIntegerField(default=0, verbose_name="تعداد کل تماس‌ها")
    successful_calls = models.PositiveIntegerField(default=0, verbose_name="تماس‌های موفق")
    last_call_date = models.DateTimeField(null=True, blank=True, verbose_name="آخرین تماس")
    last_call_result = models.CharField(max_length=50, blank=True, verbose_name="نتیجه آخرین تماس")
    response_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="نرخ پاسخ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "آمار تماس"
        verbose_name_plural = "آمار تماس‌ها"
        unique_together = ['contact', 'project']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.contact.full_name} - {self.project.name}"

    def update_statistics(self):
        """به‌روزرسانی آمار بر اساس تماس‌های موجود"""
        calls = Call.objects.filter(contact=self.contact, project=self.project)

        self.total_calls = calls.count()
        self.successful_calls = calls.filter(call_result='answered').count()

        if calls.exists():
            last_call = calls.order_by('-call_date').first()
            self.last_call_date = last_call.call_date
            self.last_call_result = last_call.call_result

        self.response_rate = (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0
        self.save()


class ExportReport(models.Model):

    EXPORT_TYPE_CHOICES = [
        ('excel', 'اکسل'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
    ]

    export_type = models.CharField(max_length=50, choices=EXPORT_TYPE_CHOICES, verbose_name="نوع صادرات")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_path = models.CharField(max_length=500, verbose_name="مسیر فایل")
    filters = models.TextField(blank=True, verbose_name="فیلترها")
    records_count = models.PositiveIntegerField(default=0, verbose_name="تعداد رکوردها")
    export_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ صادرات")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='export_reports',
                                verbose_name="پروژه")
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='export_reports',
                                    verbose_name="صادر شده توسط")

    class Meta:
        verbose_name = "گزارش صادر شده"
        verbose_name_plural = "گزارش‌های صادر شده"
        ordering = ['-export_date']

    def __str__(self):
        return f"{self.file_name} - {self.exported_by.get_full_name()}"

    def get_filters(self):
        """دریافت فیلترها به صورت dict"""
        if self.filters:
            try:
                return json.loads(self.filters)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_filters(self, filters_dict):
        """تنظیم فیلترها"""
        if filters_dict:
            self.filters = json.dumps(filters_dict, ensure_ascii=False)
        else:
            self.filters = ""
