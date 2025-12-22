# Simple test to check if the chatbot endpoint exists
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(r'd:\A prashant\Room-Rental-System (1)\Room-Rental-System')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'roombook.settings')
django.setup()

# Now test the view directly
from rooms.views import api_chatbot_message
from django.test import RequestFactory
from django.contrib.auth.models import User
from rooms.genai_chatbot import RoomBookChatbot

# Create a test request
factory = RequestFactory()
user = User.objects.first()  # Get first user for testing

# Test data
test_data = {
    'message': 'Hello, this is a test message'
}

# Create POST request
request = factory.post('/api/chatbot/message/', 
                      data=test_data, 
                      content_type='application/json')
request.user = user

print("Testing chatbot view directly...")
try:
    response = api_chatbot_message(request)
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Test chatbot directly
print("\nTesting chatbot class directly...")
try:
    chatbot = RoomBookChatbot()
    response = chatbot.generate_response(
        message="Hello, how do I book a room?",
        user=user,
        room_id=None
    )
    print(f"Chatbot response: {response}")
except Exception as e:
    print(f"Chatbot error: {e}")
    import traceback
    traceback.print_exc()
