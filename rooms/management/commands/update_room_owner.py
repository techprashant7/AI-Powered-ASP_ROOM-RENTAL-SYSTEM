from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rooms.models import Room

class Command(BaseCommand):
    help = 'Update room ownership to specified user'

    def handle(self, *args, **options):
        # Get or create the user
        user_email = 'bprashant23cs@student.mes.ac.in'
        username = user_email.split('@')[0]
        
        user, created = User.objects.get_or_create(
            email=user_email,
            defaults={
                'username': username,
                'first_name': 'Prashant',
                'is_staff': True  # Make staff so they can manage rooms
            }
        )
        
        if created:
            # Set password
            user.set_password('pr@sh@nt777777')
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created user: {user.email}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'User already exists: {user.email}')
            )
        
        # Get the 5 newest rooms (the sample rooms we just created)
        newest_rooms = Room.objects.order_by('-created_at')[:5]
        
        updated_count = 0
        for room in newest_rooms:
            room.owner = user
            room.save()
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Updated ownership for: {room.title}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} rooms to owner {user.email}')
        )
        
        # Display current room ownership
        self.stdout.write('\nCurrent room ownership:')
        for room in Room.objects.order_by('-created_at')[:5]:
            self.stdout.write(f'  - {room.title}: {room.owner.email}')
