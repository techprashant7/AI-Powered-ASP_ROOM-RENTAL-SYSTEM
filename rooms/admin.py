from django.contrib import admin
from .models import Room, Booking, UserProfile, Notification, Invoice, Payment

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

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'email_verified', 'staff_requested', 'staff_approved']
    list_filter = ['email_verified', 'staff_requested', 'staff_approved']
    search_fields = ['user__username', 'phone']

    actions = ['approve_staff_access']

    def approve_staff_access(self, request, queryset):
        for profile in queryset:
            profile.staff_approved = True
            profile.save()
            profile.user.is_staff = True
            profile.user.save()

    approve_staff_access.short_description = 'Approve selected profiles as staff'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'booking', 'status', 'total_amount', 'issued_date', 'due_date']
    list_filter = ['status', 'issued_date', 'due_date']
    search_fields = ['invoice_number', 'booking__room__title']
    readonly_fields = ['invoice_number', 'issued_date', 'created_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'invoice', 'payment_method', 'amount', 'status', 'payment_date', 'created_at']
    list_filter = ['payment_method', 'status', 'payment_date', 'created_at']
    search_fields = ['transaction_id', 'invoice__invoice_number']
    readonly_fields = ['created_at', 'updated_at']
