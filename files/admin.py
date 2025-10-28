from django.contrib import admin

from .models import *


# Register your models here.


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', "text"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["text"]


admin.site.register(SavedSearch)
admin.site.register(UploadedFile)
admin.site.register(ExportReport)
