from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.models import User
from .models import Room, Booking, UserProfile, Notification, Invoice, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class RoomSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_phone = serializers.CharField(source='phone', read_only=True)
    owner_email = serializers.CharField(source='email', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = ['id', 'title', 'description', 'price', 'location', 'image', 'image_url',
                  'phone', 'email', 'owner', 'owner_name', 'owner_phone', 'owner_email', 'created_at']
        read_only_fields = ['owner', 'created_at', 'image_url', 'owner_name', 'owner_phone', 'owner_email']
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get('request')
        name = (getattr(obj.image, 'name', '') or '').lstrip('/')

        if name and '/' not in name and name.lower().startswith('r') and name.lower().endswith('.jpg'):
            rel = f"images/about/{name}"
            url = f"{settings.STATIC_URL}{rel}"
            return request.build_absolute_uri(url) if request else url

        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

class BookingSerializer(serializers.ModelSerializer):
    room_title = serializers.CharField(source='room.title', read_only=True)
    room_location = serializers.CharField(source='room.location', read_only=True)
    room_price = serializers.DecimalField(source='room.price', max_digits=10, decimal_places=2, read_only=True)
    user_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    invoice_id = serializers.SerializerMethodField()
    invoice_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ['id', 'room', 'room_title', 'room_location', 'room_price',
                  'user', 'user_name', 'owner', 'owner_name',
                  'start_date', 'end_date', 'months', 'total_rent', 'status', 'created_at', 'invoice_id', 'invoice_status']
        read_only_fields = ['user', 'owner', 'total_rent', 'end_date', 'invoice_id', 'invoice_status']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username
    
    def get_invoice_id(self, obj):
        try:
            return obj.invoice.id
        except Invoice.DoesNotExist:
            return None
    
    def get_invoice_status(self, obj):
        try:
            return obj.invoice.status
        except Invoice.DoesNotExist:
            return None

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone', 'address']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

class InvoiceSerializer(serializers.ModelSerializer):
    booking_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = ['id', 'booking', 'booking_details', 'invoice_number', 'issued_date', 'due_date',
                  'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'status', 'pdf_file', 'created_at']
        read_only_fields = ['id', 'issued_date', 'created_at', 'pdf_file']
    
    def get_booking_details(self, obj):
        return {
            'room_title': obj.booking.room.title,
            'room_location': obj.booking.room.location,
            'user_name': f"{obj.booking.user.first_name} {obj.booking.user.last_name}".strip() or obj.booking.user.username,
            'start_date': obj.booking.start_date,
            'end_date': obj.booking.end_date,
            'months': obj.booking.months
        }

class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'invoice_number', 'payment_method', 'transaction_id',
                  'amount', 'status', 'payment_date', 'gateway_response', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at', 'payment_date']
