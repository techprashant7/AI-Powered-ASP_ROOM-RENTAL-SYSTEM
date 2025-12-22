import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os
from django.conf import settings
from django.db import models
from .models import Room, Booking

class PriceRecommendationSystem:
    """AI Price Recommendation System using ML models"""
    
    def __init__(self):
        self.models = {
            'linear_regression': LinearRegression(),
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42)
        }
        self.scalers = {}
        self.encoders = {}
        self.feature_columns = []
        self.target_column = 'price'
        
    def prepare_data(self):
        """Prepare training data from existing rooms and bookings"""
        rooms_data = []
        
        for room in Room.objects.all():
            # Extract features
            features = {
                'price': float(room.price),
                'location': room.location,
                'title_length': len(room.title),
                'has_image': bool(room.image),
            }
            
            # Add booking-based features
            bookings = Booking.objects.filter(room=room)
            if bookings.exists():
                features['total_bookings'] = bookings.count()
                features['avg_booking_duration'] = bookings.aggregate(
                    avg_duration=models.Avg(
                        models.F('end_date') - models.F('start_date')
                    )
                )['avg_duration'].days if bookings.exists() else 0
                features['occupancy_rate'] = bookings.filter(status='approved').count() / bookings.count()
            else:
                features['total_bookings'] = 0
                features['avg_booking_duration'] = 0
                features['occupancy_rate'] = 0
            
            # Location-based features
            location_features = self._extract_location_features(room.location)
            features.update(location_features)
            
            rooms_data.append(features)
        
        return pd.DataFrame(rooms_data)
    
    def _extract_location_features(self, location):
        """Extract features from location string"""
        features = {}
        
        # Common location keywords that affect price
        premium_keywords = ['downtown', 'city center', 'prime', 'central', 'luxury']
        budget_keywords = ['suburb', 'outskirts', 'affordable', 'budget']
        
        location_lower = location.lower()
        
        features['is_premium_location'] = any(keyword in location_lower for keyword in premium_keywords)
        features['is_budget_location'] = any(keyword in location_lower for keyword in budget_keywords)
        features['location_word_count'] = len(location.split())
        
        return features
    
    def preprocess_data(self, df):
        """Preprocess data for ML training"""
        df_processed = df.copy()
        
        # Handle categorical variables
        categorical_columns = ['location']
        for col in categorical_columns:
            if col in df_processed.columns:
                if col not in self.encoders:
                    self.encoders[col] = LabelEncoder()
                    df_processed[f'{col}_encoded'] = self.encoders[col].fit_transform(df_processed[col].astype(str))
                else:
                    df_processed[f'{col}_encoded'] = self.encoders[col].transform(df_processed[col].astype(str))
        
        # Select feature columns
        feature_columns = [col for col in df_processed.columns if col != self.target_column]
        feature_columns = [col for col in feature_columns if not col.endswith('_encoded') or col.replace('_encoded', '') in categorical_columns]
        
        # Add encoded columns
        for col in categorical_columns:
            if f'{col}_encoded' in df_processed.columns:
                feature_columns.append(f'{col}_encoded')
        
        self.feature_columns = feature_columns
        
        # Scale features
        X = df_processed[feature_columns].fillna(0)
        y = df_processed[self.target_column]
        
        if 'scaler' not in self.scalers:
            self.scalers['scaler'] = StandardScaler()
            X_scaled = self.scalers['scaler'].fit_transform(X)
        else:
            X_scaled = self.scalers['scaler'].transform(X)
        
        return X_scaled, y
    
    def train_models(self):
        """Train all ML models"""
        try:
            # Prepare data
            df = self.prepare_data()
            if len(df) < 5:  # Need minimum data for training
                return False, "Not enough data to train models"
            
            X, y = self.preprocess_data(df)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            results = {}
            
            # Train each model
            for name, model in self.models.items():
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                # Calculate metrics
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                results[name] = {
                    'mse': mse,
                    'r2': r2,
                    'model': model
                }
            
            # Save the best model
            best_model_name = max(results.keys(), key=lambda x: results[x]['r2'])
            self.best_model = results[best_model_name]['model']
            self.best_model_name = best_model_name
            
            # Save models to disk
            self.save_models()
            
            return True, f"Models trained successfully. Best model: {best_model_name} (R²: {results[best_model_name]['r2']:.3f})"
            
        except Exception as e:
            return False, f"Training failed: {str(e)}"
    
    def predict_price(self, room_features):
        """Predict optimal price for a room"""
        try:
            if not hasattr(self, 'best_model'):
                self.load_models()
            
            # Prepare features
            df = pd.DataFrame([room_features])
            
            # Extract location features
            if 'location' in room_features:
                location_features = self._extract_location_features(room_features['location'])
                for key, value in location_features.items():
                    df[key] = value
            
            # Encode categorical variables
            for col, encoder in self.encoders.items():
                if col in df.columns:
                    if col in room_features:
                        try:
                            df[f'{col}_encoded'] = encoder.transform([room_features[col]])
                        except ValueError:
                            # Handle unseen categories
                            df[f'{col}_encoded'] = 0
                    else:
                        df[f'{col}_encoded'] = 0
            
            # Select and scale features
            X = df[self.feature_columns].fillna(0)
            X_scaled = self.scalers['scaler'].transform(X)
            
            # Make prediction
            predicted_price = self.best_model.predict(X_scaled)[0]
            
            # Ensure price is reasonable
            predicted_price = max(50, min(10000, predicted_price))  # Min $50, Max $10000
            
            return round(predicted_price, 2)
            
        except Exception as e:
            return None
    
    def save_models(self):
        """Save trained models to disk"""
        try:
            models_dir = os.path.join(settings.BASE_DIR, 'ml_models')
            os.makedirs(models_dir, exist_ok=True)
            
            # Save the best model
            joblib.dump(self.best_model, os.path.join(models_dir, 'price_prediction_model.pkl'))
            
            # Save encoders and scalers
            joblib.dump(self.encoders, os.path.join(models_dir, 'price_encoders.pkl'))
            joblib.dump(self.scalers, os.path.join(models_dir, 'price_scalers.pkl'))
            joblib.dump(self.feature_columns, os.path.join(models_dir, 'price_features.pkl'))
            
            return True
        except Exception as e:
            return False
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            models_dir = os.path.join(settings.BASE_DIR, 'ml_models')
            
            # Load the best model
            self.best_model = joblib.load(os.path.join(models_dir, 'price_prediction_model.pkl'))
            
            # Load encoders and scalers
            self.encoders = joblib.load(os.path.join(models_dir, 'price_encoders.pkl'))
            self.scalers = joblib.load(os.path.join(models_dir, 'price_scalers.pkl'))
            self.feature_columns = joblib.load(os.path.join(models_dir, 'price_features.pkl'))
            
            return True
        except Exception as e:
            return False

class RoomRecommendationSystem:
    """Room Recommendation System using collaborative filtering and content-based filtering"""
    
    def __init__(self):
        self.user_item_matrix = None
        self.room_features = None
        
    def build_user_item_matrix(self):
        """Build user-item interaction matrix"""
        bookings = Booking.objects.filter(status='approved').select_related('user', 'room')
        
        # Create user-item matrix
        users = list(set(booking.user for booking in bookings))
        rooms = list(set(booking.room for booking in bookings))
        
        user_ids = {user.id: idx for idx, user in enumerate(users)}
        room_ids = {room.id: idx for idx, room in enumerate(rooms)}
        
        matrix = np.zeros((len(users), len(rooms)))
        
        for booking in bookings:
            user_idx = user_ids[booking.user.id]
            room_idx = room_ids[booking.room.id]
            matrix[user_idx, room_idx] = 1  # User booked this room
        
        self.user_item_matrix = matrix
        self.user_ids = user_ids
        self.room_ids = room_ids
        self.id_to_room = {idx: room for room, idx in room_ids.items()}
        
        return matrix
    
    def collaborative_filtering_recommendations(self, user_id, n_recommendations=10):
        """Generate recommendations using collaborative filtering"""
        try:
            if self.user_item_matrix is None:
                self.build_user_item_matrix()
            
            if user_id not in self.user_ids:
                return []
            
            user_idx = self.user_ids[user_id]
            
            # Calculate user similarity (cosine similarity)
            user_vector = self.user_item_matrix[user_idx]
            similarities = np.dot(self.user_item_matrix, user_vector)
            
            # Find similar users
            similar_users = np.argsort(similarities)[::-1][1:11]  # Top 10 similar users
            
            # Get rooms booked by similar users but not by current user
            recommendations = []
            user_booked_rooms = set(np.where(user_vector > 0)[0])
            
            for similar_user_idx in similar_users:
                similar_user_vector = self.user_item_matrix[similar_user_idx]
                similar_user_rooms = np.where(similar_user_vector > 0)[0]
                
                for room_idx in similar_user_rooms:
                    if room_idx not in user_booked_rooms:
                        room_id = self.id_to_room[room_idx]
                        room = Room.objects.filter(id=room_id).first()
                        if room:
                            recommendations.append({
                                'room': room,
                                'score': similarities[similar_user_idx],
                                'method': 'collaborative'
                            })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            return []
    
    def content_based_recommendations(self, user_id, n_recommendations=10):
        """Generate recommendations using content-based filtering"""
        try:
            # Get user's booking history
            user_bookings = Booking.objects.filter(user_id=user_id, status='approved').select_related('room')
            
            if not user_bookings:
                return []
            
            # Analyze user preferences
            user_locations = [booking.room.location for booking in user_bookings]
            user_prices = [booking.room.price for booking in user_bookings]
            
            avg_price = np.mean(user_prices) if user_prices else 0
            preferred_locations = list(set(user_locations))
            
            # Find similar rooms
            available_rooms = Room.objects.exclude(
                id__in=[booking.room.id for booking in user_bookings]
            )
            
            recommendations = []
            
            for room in available_rooms:
                score = 0
                
                # Location similarity
                if room.location in preferred_locations:
                    score += 0.4
                
                # Price similarity
                if avg_price > 0:
                    price_diff = abs(room.price - avg_price) / avg_price
                    if price_diff < 0.2:  # Within 20% of average price
                        score += 0.3
                    elif price_diff < 0.4:  # Within 40% of average price
                        score += 0.2
                
                # Base score for availability
                score += 0.1
                
                recommendations.append({
                    'room': room,
                    'score': score,
                    'method': 'content'
                })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:n_recommendations]
            
        except Exception as e:
            return []
    
    def get_hybrid_recommendations(self, user_id, n_recommendations=10):
        """Generate hybrid recommendations combining collaborative and content-based filtering"""
        try:
            collab_recs = self.collaborative_filtering_recommendations(user_id, n_recommendations)
            content_recs = self.content_based_recommendations(user_id, n_recommendations)
            
            # If no recommendations from either method, provide popular rooms
            if not collab_recs and not content_recs:
                return self.get_popular_rooms_recommendations(n_recommendations)
            
            # Combine recommendations
            all_recommendations = {}
            
            # Add collaborative recommendations
            for rec in collab_recs:
                room_id = rec['room'].id
                all_recommendations[room_id] = {
                    'room': rec['room'],
                    'collaborative_score': rec['score'],
                    'content_score': 0,
                    'method': 'collaborative'
                }
            
            # Add content-based recommendations
            for rec in content_recs:
                room_id = rec['room'].id
                if room_id in all_recommendations:
                    all_recommendations[room_id]['content_score'] = rec['score']
                    all_recommendations[room_id]['method'] = 'hybrid'
                else:
                    all_recommendations[room_id] = {
                        'room': rec['room'],
                        'collaborative_score': 0,
                        'content_score': rec['score'],
                        'method': 'content'
                    }
            
            # Calculate hybrid score
            for rec in all_recommendations.values():
                rec['hybrid_score'] = (rec['collaborative_score'] * 0.6 + rec['content_score'] * 0.4)
            
            # Sort by hybrid score
            sorted_recs = sorted(all_recommendations.values(), key=lambda x: x['hybrid_score'], reverse=True)
            
            return sorted_recs[:n_recommendations]
            
        except Exception as e:
            return self.get_popular_rooms_recommendations(n_recommendations)

    def get_popular_rooms_recommendations(self, n_recommendations=10):
        """Get popular rooms as fallback recommendations"""
        try:
            # Get available rooms with some basic scoring
            available_rooms = Room.objects.all()[:n_recommendations]
            
            recommendations = []
            for i, room in enumerate(available_rooms):
                # Basic scoring based on room features
                score = 0.5  # Base score
                
                # Add some variety to scores
                if room.price < 1000:
                    score += 0.2  # Affordable rooms get higher score
                if len(room.title) > 10:
                    score += 0.1  # Descriptive titles get slight boost
                
                recommendations.append({
                    'room': room,
                    'collaborative_score': 0,
                    'content_score': score,
                    'method': 'popular',
                    'hybrid_score': score
                })
            
            # Sort by score
            recommendations.sort(key=lambda x: x['hybrid_score'], reverse=True)
            return recommendations
            
        except Exception as e:
            return []
