from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rooms.models import Room

class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **kwargs):
        owner1, _ = User.objects.get_or_create(
            username='john_owner',
            defaults={
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Smith'
            }
        )
        owner1.set_password('owner123')
        owner1.save()

        owner2, _ = User.objects.get_or_create(
            username='sarah_owner',
            defaults={
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Johnson'
            }
        )
        owner2.set_password('owner123')
        owner2.save()

        user1, _ = User.objects.get_or_create(
            username='mike_user',
            defaults={
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Brown'
            }
        )
        user1.set_password('user123')
        user1.save()

        rooms_data = [
            {
                'owner': owner1,
                'title': 'Cozy Studio Apartment',
                'description': 'Beautiful studio apartment with modern amenities. Features a fully equipped kitchen, comfortable bed, and a spacious bathroom. Perfect for students or young professionals.',
                'price': 800.00,
                'location': '123 Main Street, Downtown',
                'phone': '+1-555-0101',
                'email': 'john@example.com'
            },
            {
                'owner': owner1,
                'title': 'Spacious 2-Bedroom Suite',
                'description': 'Large 2-bedroom apartment with panoramic city views. Includes living room, dining area, and balcony. Close to public transportation and shopping centers.',
                'price': 1500.00,
                'location': '456 Oak Avenue, Uptown',
                'phone': '+1-555-0101',
                'email': 'john@example.com'
            },
            {
                'owner': owner2,
                'title': 'Modern Loft Space',
                'description': 'Trendy loft with high ceilings and exposed brick walls. Open floor plan with industrial-style design. Ideal for creative professionals.',
                'price': 1200.00,
                'location': '789 Art District Lane',
                'phone': '+1-555-0202',
                'email': 'sarah@example.com'
            },
            {
                'owner': owner2,
                'title': 'Garden View Room',
                'description': 'Peaceful single room overlooking a beautiful garden. Shared bathroom and kitchen facilities. Great for nature lovers seeking tranquility.',
                'price': 550.00,
                'location': '321 Green Park Road',
                'phone': '+1-555-0202',
                'email': 'sarah@example.com'
            },
            {
                'owner': owner1,
                'title': 'Executive Business Suite',
                'description': 'Premium furnished apartment with home office setup. High-speed internet, meeting room access, and 24/7 concierge service. Perfect for business travelers.',
                'price': 2000.00,
                'location': '555 Business Plaza, Financial District',
                'phone': '+1-555-0101',
                'email': 'john@example.com'
            },
        ]

        for room_data in rooms_data:
            Room.objects.get_or_create(
                title=room_data['title'],
                defaults=room_data
            )

        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('Test accounts:')
        self.stdout.write('  Owner 1: john_owner / owner123')
        self.stdout.write('  Owner 2: sarah_owner / owner123')
        self.stdout.write('  User: mike_user / user123')
