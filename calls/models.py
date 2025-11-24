from django.conf import settings
from django.db import models
import json

from calls.calls_import import Contact, Question, AnswerChoice, Project


# Model for storing call records
class Call(models.Model):
    """Model for storing call records"""

    CALL_RESULT_CHOICES = [
        ('interested', 'Interested'),
        ('no_time', 'No time'),
        ('not_interested', 'Not interested'),
    ]

    CALL_STATUS_CHOICES = [
        ('wrong_number', 'Wrong number'),
        ('answered', 'Answered'),
        ('no_answer', 'No answer'),
        ('pending', "Pending"),
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='calls', verbose_name="Contact")
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calls',
        verbose_name="Caller"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='calls',
        verbose_name="Project"
    )
    call_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Call Date",
        db_index=True
    )
    call_result = models.CharField(
        max_length=50,
        choices=CALL_RESULT_CHOICES,
        verbose_name="Call Result",
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        choices=CALL_STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    feedback = models.TextField(blank=True, verbose_name="Feedback")
    detailed_report = models.TextField(blank=True, verbose_name="Detailed Report")
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Call Duration (seconds)"
    )
    follow_up_required = models.BooleanField(default=False, verbose_name="Requires Follow-up")
    follow_up_date = models.DateTimeField(null=True, blank=True, verbose_name="Follow-up Date")

    is_editable = models.BooleanField(default=True, verbose_name="Editable")
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name="Edited At")
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_calls',
        verbose_name="Edited By"
    )
    edit_reason = models.TextField(blank=True, verbose_name="Edit Reason")

    original_data = models.JSONField(blank=True, verbose_name="Original Data")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def can_edit(self, user):
        if not self.is_editable:
            return False
        if user.is_superuser:
            return True
        try:
            membership = ProjectMembership.objects.get(project=self.project, user=user)
            if membership.role == 'admin' or self.caller == user:
                return True
        except ProjectMembership.DoesNotExist:
            return False
        return False

    def save_original_data_if_first_edit(self):
        """Store original call data only on first edit"""
        if not self.original_data:
            original = {
                'call_result': self.call_result,
                'notes': self.notes,
                'duration': self.duration,
                'follow_up_required': self.follow_up_required,
                'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None
            }
            self.original_data = original

    def save(self, *args, **kwargs):
        self.save_original_data_if_first_edit()
        super().save(*args, **kwargs)
        self.update_call_statistics()

    def update_call_statistics(self):
        """Update call statistics for the contact/project"""
        stats, created = CallStatistics.objects.get_or_create(contact=self.contact, project=self.project)
        stats.update_statistics()

    class Meta:
        verbose_name = "Call"
        verbose_name_plural = "Calls"
        ordering = ['-call_date']
        indexes = [
            models.Index(fields=['call_date']),
            models.Index(fields=['contact']),
            models.Index(fields=['project']),
        ]

    def __str__(self):
        return f"{self.contact.full_name} - {self.caller.get_full_name()} - {self.get_call_result_display()}"

    def get_original_data(self):
        """Return original data as dict"""
        return self.original_data if self.original_data else {}

    def set_original_data(self, data_dict):
        """Set original data"""
        self.original_data = data_dict if data_dict else {}


# Model for storing edit history of calls
class CallEditHistory(models.Model):
    """Model for storing the edit history of calls"""

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name='edit_history',
        verbose_name="Call"
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='call_edits',
        verbose_name="Edited By"
    )
    edit_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Edit Date",
        db_index=True
    )
    field_name = models.CharField(max_length=50, verbose_name="Field Name")
    old_value = models.TextField(blank=True, verbose_name="Old Value")
    new_value = models.TextField(blank=True, verbose_name="New Value")
    edit_reason = models.TextField(blank=True, verbose_name="Edit Reason")

    class Meta:
        verbose_name = "Call Edit History"
        verbose_name_plural = "Call Edit Histories"
        ordering = ['-edit_date']
        indexes = [
            models.Index(fields=['edit_date']),
        ]

    def __str__(self):
        return f"{self.call.id} - {self.field_name} - {self.edited_by.get_full_name()}"


# Model for storing answers to call questions
class CallAnswer(models.Model):
    """Model for storing answers to questions asked during a call"""

    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='answers', verbose_name="Call")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Question")
    selected_choice = models.ForeignKey(
        AnswerChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Selected Choice"
    )

    class Meta:
        unique_together = ('call', 'question')  # Prevent duplicate answers for same call-question pair
        verbose_name = "Call Answer"
        verbose_name_plural = "Call Answers"

    def __str__(self):
        return f"{self.call} - {self.question.text}"
