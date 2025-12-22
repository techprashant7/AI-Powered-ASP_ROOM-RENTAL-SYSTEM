from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rooms.models import Room, Booking
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Add sample data for testing'

    def handle(self, *args, **options):
        # Create sample rooms
        sample_rooms = [
            {
                'title': 'Cozy Downtown Studio',
                'location': 'Downtown City Center',
                'description': 'Modern studio apartment in the heart of downtown with city views',
                'price': 800.00,
            },
            {
                'title': 'Spacious Suburban Home',
                'location': 'Quiet Suburbs',
                'description': 'Large family home with garden and parking',
                'price': 1200.00,
            },
            {
                'title': 'Beachfront Paradise',
                'location': 'Coastal Area',
                'description': 'Beautiful beachfront room with ocean views',
                'price': 1500.00,
            },
            {
                'title': 'Mountain Retreat',
                'location': 'Mountain Region',
                'description': 'Peaceful mountain cabin with scenic views',
                'price': 900.00,
            },
            {
                'title': 'Urban Loft',
                'location': 'City Center',
                'description': 'Stylish loft in trendy urban neighborhood',
                'price': 1100.00,
            }
        ]

        created_rooms = []
        for room_data in sample_rooms:
            # Get or create a staff user as owner
            owner, created = User.objects.get_or_create(
                username=f'owner_{room_data["location"].lower().replace(" ", "_")}',
                defaults={
                    'email': f'owner_{room_data["location"].lower().replace(" ", "_")}@example.com',
                    'is_staff': True
                }
            )
            
            room, created = Room.objects.get_or_create(
                title=room_data['title'],
                defaults={
                    'owner': owner,
                    'location': room_data['location'],
                    'description': room_data['description'],
                    'price': room_data['price']
                }
            )
            
            if created:
                created_rooms.append(room)
                self.stdout.write(
                    self.style.SUCCESS(f'Created room: {room.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Room already exists: {room.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(created_rooms)} sample rooms')
        )

        # Create some sample bookings if users exist
        users = User.objects.filter(is_staff=False)[:3]
        if users and created_rooms:
            for user in users:
                room = random.choice(created_rooms)
                start_date = datetime.now().date() + timedelta(days=random.randint(1, 30))
                end_date = start_date + timedelta(days=random.randint(1, 7))
                
                booking, created = Booking.objects.get_or_create(
                    user=user,
                    room=room,
                    defaults={
                        'owner': room.owner,
                        'start_date': start_date,
                        'end_date': end_date,
                        'months': ((end_date - start_date).days // 30) + 1,
                        'total_rent': room.price * ((end_date - start_date).days),
                        'status': 'approved'
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created booking for {user.username}')
                    )

        self.stdout.write(
            self.style.SUCCESS('Sample data creation completed!')
        )
