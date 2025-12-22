import json
import os
from django.conf import settings
from openai import OpenAI
from .models import Room, Booking
from .ml_models import PriceRecommendationSystem

class AINegotiationAssistant:
    """AI-powered rent negotiation assistant that acts as a smart mediator"""
    
    def __init__(self):
        self.client = None
        self.price_system = PriceRecommendationSystem()
        self.setup_openai()
        
    def setup_openai(self):
        """Setup OpenAI client"""
        try:
            api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv('OPENAI_API_KEY'))
            if api_key:
                self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI setup failed: {e}")
    
    def get_market_price(self, room_id):
        """Get market price for the room using ML prediction"""
        try:
            room = Room.objects.get(id=room_id)
            room_features = {
                'location': room.location,
                'title_length': len(room.title),
                'has_image': bool(room.image)
            }
            
            # Try to get ML prediction
            predicted_price = self.price_system.predict_price(room_features)
            if predicted_price:
                return predicted_price
            
            # Fallback: use current price as market price
            return float(room.price)
            
        except Room.DoesNotExist:
            return None
    
    def analyze_negotiation_scenario(self, owner_min_price, tenant_offer, market_price):
        """Analyze the negotiation scenario and generate insights"""
        owner_min = float(owner_min_price)
        tenant_off = float(tenant_offer)
        market = float(market_price)
        
        # Calculate gaps
        owner_tenant_gap = owner_min - tenant_off
        market_owner_gap = market - owner_min
        market_tenant_gap = market - tenant_off
        
        # Determine negotiation position
        if tenant_off >= owner_min:
            position = "tenant_acceptable"
        elif tenant_off >= market:
            position = "tenant_generous"
        elif tenant_off >= owner_min * 0.9:
            position = "close_to_deal"
        else:
            position = "significant_gap"
        
        return {
            'position': position,
            'owner_tenant_gap': owner_tenant_gap,
            'market_owner_gap': market_owner_gap,
            'market_tenant_gap': market_tenant_gap,
            'owner_min_price': owner_min,
            'tenant_offer': tenant_off,
            'market_price': market
        }
    
    def generate_negotiation_response(self, room_id, owner_min_price, tenant_offer, negotiation_tone="polite"):
        """Generate AI-powered negotiation response"""
        try:
            # Get market price
            market_price = self.get_market_price(room_id)
            if not market_price:
                return "Unable to determine market price for this room."
            
            # Analyze scenario
            analysis = self.analyze_negotiation_scenario(owner_min_price, tenant_offer, market_price)
            
            # Generate response using OpenAI if available
            if self.client:
                try:
                    response = self._generate_openai_response(analysis, negotiation_tone)
                    return response
                except Exception as e:
                    print(f"OpenAI error: {e}")
            
            # Fallback to rule-based response
            return self._generate_fallback_response(analysis)
            
        except Exception as e:
            print(f"Negotiation error: {e}")
            return "I encountered an error while analyzing the negotiation. Please try again."
    
    def _generate_openai_response(self, analysis, tone):
        """Generate response using OpenAI"""
        prompt = f"""
You are a professional rent negotiation mediator. Analyze this scenario and provide a helpful, {tone} response.

Scenario Details:
- Owner's minimum acceptable price: ₹{analysis['owner_min_price']:,.2f}
- Tenant's current offer: ₹{analysis['tenant_offer']:,.2f}
- Market price prediction: ₹{analysis['market_price']:,.2f}
- Gap between owner and tenant: ₹{analysis['owner_tenant_gap']:,.2f}

Negotiation Position: {analysis['position']}

Provide a response that:
1. Acknowledges both parties' positions
2. Explains the market context
3. Suggests a fair compromise price
4. Provides reasoning for the suggestion
5. Maintains a professional and helpful tone

Keep the response concise but comprehensive (2-3 sentences).
"""
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional rent negotiation mediator helping both parties reach a fair agreement."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def _generate_fallback_response(self, analysis):
        """Generate rule-based response when OpenAI is not available"""
        position = analysis['position']
        market = analysis['market_price']
        
        if position == "tenant_acceptable":
            return f"Great news! The tenant's offer of ₹{analysis['tenant_offer']:,.2f} meets or exceeds your minimum. This appears to be a fair deal based on current market rates."
        
        elif position == "tenant_generous":
            return f"The tenant's offer of ₹{analysis['tenant_offer']:,.2f} is above market value. You might consider accepting this generous offer while it's available."
        
        elif position == "close_to_deal":
            suggested_price = (analysis['owner_min_price'] + analysis['tenant_offer']) / 2
            return f"You're very close to an agreement! A fair compromise would be ₹{suggested_price:,.2f}, which is reasonable given the market price of ₹{market:,.2f}."
        
        else:  # significant_gap
            suggested_price = market * 0.95  # 5% below market
            return f"Based on market analysis of ₹{market:,.2f}, a fair negotiated rent would be ₹{suggested_price:,.2f}. This accounts for current demand while being reasonable for both parties."
    
    def get_negotiation_tips(self, position):
        """Get negotiation tips based on current position"""
        tips = {
            "tenant_acceptable": [
                "This is a solid offer that meets your requirements",
                "Consider accepting to secure the tenant quickly",
                "You're in a good negotiating position"
            ],
            "tenant_generous": [
                "This offer is above market value - act quickly",
                "The tenant seems very interested in your property",
                "You have room to negotiate if needed"
            ],
            "close_to_deal": [
                "You're very close to reaching an agreement",
                "A small compromise could seal the deal",
                "Consider meeting in the middle"
            ],
            "significant_gap": [
                "There's a substantial gap to bridge",
                "Focus on the value your property provides",
                "Consider offering incentives or flexible terms"
            ]
        }
        
        return tips.get(position, ["Continue negotiating to find common ground"])
