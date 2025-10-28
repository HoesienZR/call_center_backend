from django.contrib import admin
from .models import Ticket
# Register your models here.


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['title','created_at','user',]
    list_filter = ['done']
    search_fields = ['title','description']
