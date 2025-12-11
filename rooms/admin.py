from django.contrib import admin
from .models import Room, Booking

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'price', 'location', 'created_at']
    list_filter = ['created_at', 'location']
    search_fields = ['title', 'description', 'location']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'user', 'owner', 'start_date', 'months', 'total_rent', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['room__title', 'user__username']
