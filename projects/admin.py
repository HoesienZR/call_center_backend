from django.contrib import admin
from .models import ProjectMembership, Project, Question, AnswerChoice

# Register your models here.

class ProjectMembershipInline(admin.TabularInline):
    """
    Allows adding and editing project members directly on the project page.
    """
    model = ProjectMembership
    extra = 1
    autocomplete_fields = ['user']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the Project model.
    """
    list_display = ('name', "id", 'status', 'created_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    autocomplete_fields = ['created_by']
    inlines = [ProjectMembershipInline]

    def get_full_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    get_full_name.short_description = 'Created By'


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for the ProjectMembership model.
    """
    list_display = ('project', 'user', 'role', 'assigned_at')
    list_filter = ('role', 'project')
    search_fields = ('project__name', 'user__username')
    autocomplete_fields = ['project', 'user']


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', "text"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["text"]
