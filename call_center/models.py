from django.db import models
from django.db.models import functions
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import json
from datetime import datetime, timedelta


class Project(models.Model):
    """مدل برای مدیریت پروژه‌های تماس مختلف"""
    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('completed', 'تکمیل شده'),
    ]

    name = models.CharField(max_length=100, verbose_name="نام پروژه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="وضعیت")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects',
                                   verbose_name="ایجاد شده توسط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ['-created_at']
        permissions = [
            ('manage_project', 'Can manage project'),
        ]
    def __str__(self):
        return self.name

    def get_statistics(self):
        """دریافت آمار کلی پروژه"""
        total_contacts = self.contacts.count()
        total_callers = self.project_callers.filter(is_active=True).count()
        total_calls = self.calls.count()

        answered_calls = self.calls.filter(call_result='answered').count()
        no_answer_calls = self.calls.filter(call_result='no_answer').count()
        busy_calls = self.calls.filter(call_result='busy').count()
        unreachable_calls = self.calls.filter(call_result='unreachable').count()
        wrong_number_calls = self.calls.filter(call_result='wrong_number').count()
        not_interested_calls = self.calls.filter(call_result='not_interested').count()
        callback_requested_calls = self.calls.filter(call_result='callback_requested').count()

        total_duration = self.calls.aggregate(models.Sum('duration'))['duration__sum'] or 0
        average_duration = (total_duration / total_calls) if total_calls > 0 else 0

        success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0

        return {
            'total_contacts': total_contacts,
            'total_callers': total_callers,
            'total_calls': total_calls,
            'call_results_distribution': {
                'answered': answered_calls,
                'no_answer': no_answer_calls,
                'busy': busy_calls,
                'unreachable': unreachable_calls,
                'wrong_number': wrong_number_calls,
                'not_interested': not_interested_calls,
                'callback_requested': callback_requested_calls,
            },
            'total_duration_seconds': total_duration,
            'average_call_duration_seconds': round(average_duration, 2),
            'success_rate': round(success_rate, 2)
        }

    def get_caller_performance_report(self):
        """دریافت گزارش عملکرد تماس‌گیرندگان برای این پروژه"""
        caller_performance = []
        for project_caller in self.project_callers.filter(is_active=True):
            caller = project_caller.caller
            calls_by_caller = self.calls.filter(caller=caller)

            total_calls = calls_by_caller.count()
            answered_calls = calls_by_caller.filter(call_result='answered').count()
            total_duration = calls_by_caller.aggregate(models.Sum('duration'))['duration__sum'] or 0

            success_rate = (answered_calls / total_calls * 100) if total_calls > 0 else 0
            average_duration = (total_duration / total_calls) if total_calls > 0 else 0

            caller_performance.append({
                'caller_id': caller.id,
                'caller_username': caller.username,
                'caller_full_name': caller.get_full_name(),
                'total_calls': total_calls,
                'answered_calls': answered_calls,
                'success_rate': round(success_rate, 2),
                'total_duration_seconds': total_duration,
                'average_call_duration_seconds': round(average_duration, 2),
            })
        return caller_performance

    def get_call_status_over_time(self, start_date=None, end_date=None, interval='day'):
        """
        دریافت وضعیت تماس‌ها در طول زمان برای داشبورد.
        interval می‌تواند 'day', 'week', 'month' باشد.
        """
        calls = self.calls.all()
        if start_date:
            calls = calls.filter(call_date__gte=start_date)
        if end_date:
            calls = calls.filter(call_date__lte=end_date)

        if interval == 'day':
            date_format = '%Y-%m-%d'
        elif interval == 'week':
            date_format = '%Y-%W'
        elif interval == 'month':
            date_format = '%Y-%m'
        else:
            raise ValueError("Invalid interval. Must be 'day', 'week', or 'month'.")

        # Group by date and call result
        data = calls.annotate(
            date=functions.Extract('call_date', interval)
        ).values('date', 'call_result').annotate(count=models.Count('id')).order_by('date', 'call_result')

        # Format for chart
        chart_data = {}
        for item in data:
            date_key = item['date']
            if date_key not in chart_data:
                chart_data[date_key] = {
                    'date': item['date'],
                    'total_calls': 0
                }
                for choice, _ in Call.CALL_RESULT_CHOICES:
                    chart_data[date_key][choice] = 0

            chart_data[date_key][item['call_result']] = item['count']
            chart_data[date_key]['total_calls'] += item['count']

        return list(chart_data.values())


class ProjectCaller(models.Model):
    """مدل برای تخصیص تماس‌گیرندگان به پروژه‌ها"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_callers', verbose_name="پروژه")
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_assignments',
                               verbose_name="تماس‌گیرنده")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تخصیص")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    def clean(self):
        if not self.caller.profile.role == 'caller':
            raise ValidationError("کاربر باید تماس‌گیرنده باشد.")
        super().clean()
    class Meta:
        verbose_name = "تخصیص تماس‌گیرنده"
        verbose_name_plural = "تخصیص تماس‌گیرندگان"
        unique_together = ['project', 'caller']
        ordering = ['assigned_at']

    def __str__(self):
        return f"{self.caller.get_full_name()} - {self.project.name}"


class Contact(models.Model):
    """مدل برای ذخیره اطلاعات مخاطبین"""
    CALL_STATUS_CHOICES = [
        ('pending', 'در انتظار تماس'),
        ('contacted', 'تماس گرفته شده'),
        ('follow_up', 'نیاز به پیگیری'),
        ('completed', 'تکمیل شده'),
        ('not_interested', 'علاقه‌مند نیست'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='contacts', verbose_name="پروژه")
    full_name = models.CharField(max_length=100, verbose_name="نام کامل")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    email = models.EmailField(blank=True, verbose_name="ایمیل")
    address = models.TextField(blank=True, verbose_name="آدرس")
    assigned_caller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_contacts',
        verbose_name="تماس‌گیرنده تخصیص داده شده"
    )
    call_status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='pending',
                                   verbose_name="وضعیت تماس")
    last_call_date = models.DateTimeField(null=True, blank=True, verbose_name="آخرین تماس")
    custom_fields = models.TextField(blank=True, verbose_name="فیلدهای سفارشی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")

    class Meta:
        verbose_name = "مخاطب"
        verbose_name_plural = "مخاطبین"
        unique_together = ['project', 'phone']
        ordering = ['full_name']
    def __str__(self):
        return f"{self.full_name} - {self.phone}"

    def get_custom_fields(self):
        """دریافت فیلدهای سفارشی به صورت dict"""
        if self.custom_fields:
            try:
                return json.loads(self.custom_fields)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_custom_fields(self, fields_dict):
        """تنظیم فیلدهای سفارشی"""
        if fields_dict:
            self.custom_fields = json.dumps(fields_dict, ensure_ascii=False)
        else:
            self.custom_fields = ""

    def get_call_statistics(self):
        """دریافت آمار تماس‌های این مخاطب"""
        try:
            stats = self.call_statistics.get(project=self.project)
            return {
                'total_calls': stats.total_calls,
                'successful_calls': stats.successful_calls,
                'response_rate': float(stats.response_rate),
                'last_call_date': stats.last_call_date,
                'last_call_result': stats.last_call_result
            }
        except CallStatistics.DoesNotExist:
            return {
                'total_calls': 0,
                'successful_calls': 0,
                'response_rate': 0.0,
                'last_call_date': None,
                'last_call_result': None
            }

    def get_last_call(self):
        """دریافت آخرین تماس"""
        last_call = self.calls.order_by('-call_date').first()
        return last_call


class Call(models.Model):
    """مدل برای ثبت تماس‌ها"""
    CALL_RESULT_CHOICES = [
        ('answered', 'پاسخ داد'),
        ('no_answer', 'پاسخ نداد'),
        ('busy', 'مشغول'),
        ('unreachable', 'در دسترس نیست'),
        ('wrong_number', 'شماره اشتباه'),
        ('not_interested', 'علاقه‌مند نیست'),
        ('callback_requested', 'درخواست تماس مجدد'),
    ]

    CALL_STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('in_progress', 'در حال انجام'),
        ('completed', 'تکمیل شده'),
        ('follow_up', 'نیاز به پیگیری'),
        ('cancelled', 'لغو شده'),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls', verbose_name="مخاطب")
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls', verbose_name="تماس‌گیرنده")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='calls', verbose_name="پروژه")
    call_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تماس")
    call_result = models.CharField(max_length=50, choices=CALL_RESULT_CHOICES, verbose_name="نتیجه تماس")
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="یادداشت‌ها")
    feedback = models.TextField(blank=True, verbose_name="بازخورد")
    detailed_report = models.TextField(blank=True, verbose_name="گزارش تفصیلی")
    duration = models.PositiveIntegerField(null=True, blank=True, verbose_name="مدت تماس (ثانیه)")
    follow_up_required = models.BooleanField(default=False, verbose_name="نیاز به پیگیری")
    follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پیگیری")
    is_editable = models.BooleanField(default=True, verbose_name="قابل ویرایش")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ ویرایش")
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_calls',
        verbose_name="ویرایش شده توسط"
    )
    edit_reason = models.TextField(blank=True, verbose_name="دلیل ویرایش")
    original_data = models.TextField(blank=True, verbose_name="داده‌های اصلی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    def can_edit(self, user):
        if not self.is_editable:
            return False
        if user.is_superuser:
            return True
        if user.profile.role == 'caller' and self.caller == user:
            return True
        return False
    class Meta:
        verbose_name = "تماس"
        verbose_name_plural = "تماس‌ها"
        ordering = ['-call_date']
    def __str__(self):
        return f"{self.contact.full_name} - {self.caller.get_full_name()} - {self.get_call_result_display()}"

    def get_original_data(self):
        """دریافت داده‌های اصلی به صورت dict"""
        if self.original_data:
            try:
                return json.loads(self.original_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_original_data(self, data_dict):
        """تنظیم داده‌های اصلی"""
        if data_dict:
            self.original_data = json.dumps(data_dict, ensure_ascii=False)
        else:
            self.original_data = ""

    def save_original_data_if_first_edit(self):
        """ذخیره داده‌های اصلی در صورت اولین ویرایش"""
        if not self.original_data:
            original = {
                'call_result': self.call_result,
                'notes': self.notes,
                'duration': self.duration,
                'follow_up_required': self.follow_up_required,
                'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None
            }
            self.set_original_data(original)

    def can_edit(self, user):
        """بررسی امکان ویرایش توسط کاربر"""
        if not self.is_editable:
            return False
        return self.caller == user

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # به‌روزرسانی آمار پس از ذخیره
        self.update_call_statistics()

    def update_call_statistics(self):
        """به‌روزرسانی آمار تماس‌ها"""
        stats, created = CallStatistics.objects.get_or_create(
            contact=self.contact,
            project=self.project
        )
        stats.update_statistics()


class CallEditHistory(models.Model):
    """مدل برای تاریخچه ویرایش تماس‌ها"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='edit_history', verbose_name="تماس")
    edited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_edits',
                                  verbose_name="ویرایش شده توسط")
    edit_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ویرایش")
    field_name = models.CharField(max_length=50, verbose_name="نام فیلد")
    old_value = models.TextField(blank=True, verbose_name="مقدار قبلی")
    new_value = models.TextField(blank=True, verbose_name="مقدار جدید")
    edit_reason = models.TextField(blank=True, verbose_name="دلیل ویرایش")

    class Meta:
        verbose_name = "تاریخچه ویرایش تماس"
        verbose_name_plural = "تاریخچه ویرایش تماس‌ها"
        ordering = ['-edit_date']

    def __str__(self):
        return f"{self.call.id} - {self.field_name} - {self.edited_by.get_full_name()}"


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


class SavedSearch(models.Model):
    """مدل برای ذخیره جستجوهای کاربران"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches', verbose_name="کاربر")
    search_name = models.CharField(max_length=100, verbose_name="نام جستجو")
    search_criteria = models.TextField(verbose_name="معیارهای جستجو")
    is_public = models.BooleanField(default=False, verbose_name="عمومی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "جستجوی ذخیره شده"
        verbose_name_plural = "جستجوهای ذخیره شده"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.search_name} - {self.user.get_full_name()}"

    def get_search_criteria(self):
        """دریافت معیارهای جستجو به صورت dict"""
        if self.search_criteria:
            try:
                return json.loads(self.search_criteria)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_search_criteria(self, criteria_dict):
        """تنظیم معیارهای جستجو"""
        if criteria_dict:
            self.search_criteria = json.dumps(criteria_dict, ensure_ascii=False)
        else:
            self.search_criteria = '{}'


class UploadedFile(models.Model):
    """مدل برای مدیریت فایل‌های آپلود شده"""
    FILE_TYPE_CHOICES = [
        ('contacts', 'مخاطبین'),
        ('callers', 'تماس‌گیرندگان'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='uploaded_files', verbose_name="پروژه")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_path = models.CharField(max_length=500, verbose_name="مسیر فایل")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name="نوع فایل")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files',
                                    verbose_name="آپلود شده توسط")
    records_count = models.PositiveIntegerField(default=0, verbose_name="تعداد رکوردها")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")

    class Meta:
        verbose_name = "فایل آپلود شده"
        verbose_name_plural = "فایل‌های آپلود شده"
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.file_name} - {self.project.name}"


class ExportReport(models.Model):
    """مدل برای گزارش‌های صادر شده"""
    EXPORT_TYPE_CHOICES = [
        ('excel', 'اکسل'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='export_reports',
                                verbose_name="پروژه")
    exported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_reports',
                                    verbose_name="صادر شده توسط")
    export_type = models.CharField(max_length=50, choices=EXPORT_TYPE_CHOICES, verbose_name="نوع صادرات")
    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_path = models.CharField(max_length=500, verbose_name="مسیر فایل")
    filters = models.TextField(blank=True, verbose_name="فیلترها")
    records_count = models.PositiveIntegerField(default=0, verbose_name="تعداد رکوردها")
    export_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ صادرات")

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

class UserProfile(models.Model):
    USER_ROLES = [
        ('caller', 'تماس‌گیرنده'),
        ('regular', 'کاربر معمولی'),
        ('admin','ادمین')

    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=USER_ROLES, default='regular', verbose_name="نقش کاربر")

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # تخصیص گروه بر اساس نقش
        from django.contrib.auth.models import Group
        group_name = 'Caller' if self.role == 'caller' else 'Regular User'
        group = Group.objects.get(name=group_name)
        self.user.groups.clear()
        self.user.groups.add(group)
# call_center/models.py
class ContactLog(models.Model):
    contact = models.ForeignKey('Contact', on_delete=models.CASCADE, related_name='logs', verbose_name="مخاطب")
    action = models.CharField(max_length=200, verbose_name="اقدام")
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="انجام شده توسط"
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        verbose_name = "لاگ مخاطب"
        verbose_name_plural = "لاگ‌های مخاطب"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} - {self.contact.full_name} at {self.timestamp}"