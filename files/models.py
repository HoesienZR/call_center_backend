from django.db import models
from django.conf import settings
from projects.models import Project
# Create your models here.


class SavedSearch(models.Model):
    """مدل برای ذخیره جستجوهای کاربران"""
    search_name = models.CharField(max_length=100, verbose_name="نام جستجو")
    search_criteria = models.TextField(verbose_name="معیارهای جستجو")
    is_public = models.BooleanField(default=False, verbose_name="عمومی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_searches',
                             verbose_name="کاربر")

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

    file_name = models.CharField(max_length=255, verbose_name="نام فایل")
    file_path = models.CharField(max_length=500, verbose_name="مسیر فایل")
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name="نوع فایل")
    records_count = models.PositiveIntegerField(default=0, verbose_name="تعداد رکوردها")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آپلود")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='uploaded_files', verbose_name="پروژه")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files',
                                    verbose_name="آپلود شده توسط")

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


class Question(models.Model):
    """مدل برای سوالات مرتبط با پروژه"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='questions', verbose_name="پروژه")
    text = models.CharField(max_length=200, verbose_name="متن سوال")

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "سوالات"

    def clean(self):
        # Enforce at most 5 questions per project
        if self.project.questions.count() >= 5:
            raise ValidationError("هر پروژه حداکثر ۵ سوال می‌تواند داشته باشد.")
        super().clean()

    def __str__(self):
        return self.text


class AnswerChoice(models.Model):
    """مدل برای گزینه‌های پاسخ هر سوال"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name="سوال")
    text = models.CharField(max_length=100, verbose_name="متن گزینه")

    class Meta:
        verbose_name = "گزینه پاسخ"
        verbose_name_plural = "گزینه‌های پاسخ"

    def __str__(self):
        return self.text

