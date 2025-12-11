from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Room, Booking

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
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class BookingSerializer(serializers.ModelSerializer):
    room_title = serializers.CharField(source='room.title', read_only=True)
    room_location = serializers.CharField(source='room.location', read_only=True)
    room_price = serializers.DecimalField(source='room.price', max_digits=10, decimal_places=2, read_only=True)
    user_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ['id', 'room', 'room_title', 'room_location', 'room_price',
                  'user', 'user_name', 'owner', 'owner_name',
                  'start_date', 'end_date', 'months', 'total_rent', 'status', 'created_at']
        read_only_fields = ['user', 'owner', 'total_rent', 'end_date']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
    
    def get_owner_name(self, obj):
        return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username
