from django.contrib import admin
from .models import Professional, Service, Booking
@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ('name','phone','email')
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name','duration_min','price')
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('client_name','service','professional','start_datetime','end_datetime','created_at')
    list_filter = ('professional','service')
    search_fields = ('client_name','client_phone')
