from django.core.management.base import BaseCommand
from rooms.models import Room

class Command(BaseCommand):
    help = 'Fix room images to use static images'
    
    def handle(self, *args, **options):
        # Map room IDs to static images
        image_mapping = {
            1: 'r1.jpg', 2: 'r2.jpg', 3: 'r3.jpg', 4: 'r4.jpg', 5: 'r5.jpg',
            6: 'r6.jpg', 7: 'r7.jpg', 8: 'r8.jpg', 9: 'r9.jpg', 10: 'r10.jpg', 11: 'r11.jpg'
        }
        
        rooms = Room.objects.all()
        for room in rooms:
            # Assign image based on room ID
            image_name = image_mapping.get(room.id, 'r1.jpg')
            room.image.name = image_name if room.image else f'room_images/{image_name}'
            room.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Updated Room {room.id}: {room.title} -> {image_name}')
            )
        
        self.stdout.write(self.style.SUCCESS('Room images updated successfully!'))
