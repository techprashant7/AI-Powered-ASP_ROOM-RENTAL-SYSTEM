from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=300)
    image = models.ImageField(upload_to='room_images/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookings')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    months = models.IntegerField()
    total_rent = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.room.title} ({self.status})"
