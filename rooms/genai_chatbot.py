import json
import os
from django.conf import settings
from openai import OpenAI
from .models import Room, Booking

class RoomBookChatbot:
    """GenAI-powered chatbot for RoomBook platform"""
    
    def __init__(self):
        self.client = None
        self.setup_openai()
        
    def setup_openai(self):
        """Setup OpenAI client"""
        try:
            # Try to get OpenAI API key from environment or settings
            api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
            if api_key:
                self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI setup failed: {e}")
    
    def get_system_prompt(self):
        """Get the system prompt for the chatbot"""
        return """You are a helpful AI assistant for RoomBook, a room rental platform. Your role is to help users with:

1. Room details and features
2. Booking process and steps
3. Agreement terms and policies
4. Nearby facilities and locations
5. General platform navigation

Guidelines:
- Be friendly, professional, and helpful
- Provide accurate information based on the context
- If you don't know something, suggest contacting support
- Keep responses concise but informative
- Focus on room rental and booking-related queries

Available actions you can help with:
- Explaining room features
- Guiding through booking steps
- Describing agreement terms
- Providing location information
- Answering platform usage questions

"""

    def get_context_info(self, user=None, room_id=None):
        """Get contextual information for the chatbot"""
        context = {
            'user': None,
            'room': None,
            'available_rooms': [],
            'user_bookings': []
        }
        
        # User information
        if user:
            context['user'] = {
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
            
            # User's bookings
            user_bookings = Booking.objects.filter(user=user).select_related('room')
            context['user_bookings'] = [
                {
                    'room_title': booking.room.title,
                    'location': booking.room.location,
                    'start_date': booking.start_date,
                    'end_date': booking.end_date,
                    'status': booking.status
                }
                for booking in user_bookings
            ]
        
        # Specific room information
        if room_id:
            try:
                room = Room.objects.get(id=room_id)
                context['room'] = {
                    'title': room.title,
                    'location': room.location,
                    'description': room.description,
                    'price': room.price,
                    'phone': room.phone,
                    'email': room.email
                }
            except Room.DoesNotExist:
                pass
        
        # Available rooms (sample of 5)
        rooms = Room.objects.all()[:5]
        context['available_rooms'] = [
            {
                'title': room.title,
                'location': room.location,
                'price': room.price,
                'description': room.description[:100] + '...' if len(room.description) > 100 else room.description
            }
            for room in rooms
        ]
        
        return context
    
    def format_context_for_prompt(self, context):
        """Format context information for the prompt"""
        prompt_parts = []
        
        if context['room']:
            room = context['room']
            prompt_parts.append(f"Current Room: {room['title']}")
            prompt_parts.append(f"Location: {room['location']}")
            prompt_parts.append(f"Price: ${room['price']}")
            prompt_parts.append(f"Contact: {room['phone']} or {room['email']}")
        
        if context['user_bookings']:
            prompt_parts.append("\nUser's Recent Bookings:")
            for booking in context['user_bookings']:
                prompt_parts.append(f"- {booking['room_title']} ({booking['location']}) - {booking['status']}")
        
        if context['available_rooms']:
            prompt_parts.append("\nAvailable Rooms:")
            for room in context['available_rooms']:
                prompt_parts.append(f"- {room['title']} ({room['location']}) - ${room['price']}")
        
        return "\n".join(prompt_parts)
    
    def generate_response(self, message, user=None, room_id=None):
        """Generate chatbot response"""
        try:
            # Get context
            context = self.get_context_info(user, room_id)
            context_text = self.format_context_for_prompt(context)
            
            # If OpenAI client is available, use it
            if self.client:
                try:
                    # Create the prompt
                    system_prompt = self.get_system_prompt()
                    user_message = f"""
{context_text}

User Query: {message}

Please provide a helpful response based on the context and your knowledge about RoomBook.
"""
                    
                    # Generate response
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    return response.choices[0].message.content.strip()
                    
                except Exception as openai_error:
                    print(f"OpenAI API error: {openai_error}")
                    # Fall back to rule-based responses
            
            # Use fallback response system
            return self.get_fallback_response(message)
            
        except Exception as e:
            print(f"Chatbot error: {e}")
            return self.get_fallback_response(message)
    
    def get_fallback_response(self, message):
        """Get fallback response when OpenAI is not available"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['book', 'booking', 'reserve']):
            return "To book a room, browse available rooms, select one that interests you, and click the 'Book Now' button. You'll need to specify your check-in and check-out dates, then wait for the owner's approval. The booking process is simple and secure!"
        
        elif any(word in message_lower for word in ['price', 'cost', 'rate', 'payment']):
            return "Room prices vary based on location, amenities, and duration. You can see the price for each room listed on the room details page. Prices are shown per night. Payment is processed securely through our platform after your booking is approved."
        
        elif any(word in message_lower for word in ['agreement', 'contract', 'terms']):
            return "Our rental agreement outlines the terms between you and the room owner. It covers payment terms, house rules, cancellation policies, and other important details. You can generate a custom agreement using our AI Agreement Generator in the menu!"
        
        elif any(word in message_lower for word in ['location', 'area', 'nearby', 'facilities']):
            return "Each room listing includes its location and nearby facilities. You can filter rooms by location to find options in your preferred area. Room descriptions often mention nearby attractions, transportation, and amenities."
        
        elif any(word in message_lower for word in ['help', 'support', 'contact']):
            return "For additional help, you can contact our support team at support@roombook.com or use the help section in your profile. I'm also here to assist you with common questions about bookings and room searches!"
        
        elif any(word in message_lower for word in ['how', 'process', 'steps']):
            return "The RoomBook process is simple: 1) Browse rooms, 2) Select your preferred room, 3) Book with your dates, 4) Wait for owner approval, 5) Pay and enjoy your stay! Each step is designed to be user-friendly and secure."
        
        elif any(word in message_lower for word in ['amenities', 'features', 'included']):
            return "Room amenities vary by property but commonly include WiFi, kitchen access, laundry facilities, and more. Each room listing details what's included, so you can choose based on your needs."
        
        elif any(word in message_lower for word in ['cancel', 'cancellation', 'refund']):
            return "Cancellation policies depend on the room owner's terms. You can find specific cancellation information in the room details and rental agreement. Some bookings may be refundable if cancelled within a certain timeframe."
        
        elif any(word in message_lower for word in ['recommendations', 'suggest', 'ai']):
            return "Try our AI Recommendations feature! It analyzes your preferences and booking history to suggest rooms you might like. You can find it in the dropdown menu under your username."
        
        else:
            return "I'm here to help you with RoomBook! I can assist with room details, booking process, payment terms, agreement information, and location details. What specific question can I help you with today?"
