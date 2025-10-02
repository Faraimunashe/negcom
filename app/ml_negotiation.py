"""
ML-powered negotiation system integration
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from app import db
from app.models import User, Vehicle, Order, Negotiation, NegotiationOffer

class MLNegotiationEngine:
    def __init__(self):
        self.price_model = None
        self.outcome_model = None
        self.feature_columns = []
        self.load_models()
    
    def load_models(self):
        """Load the trained ML models"""
        model_dir = 'models'
        try:
            if os.path.exists(os.path.join(model_dir, 'price_model.pkl')):
                self.price_model = joblib.load(os.path.join(model_dir, 'price_model.pkl'))
            
            if os.path.exists(os.path.join(model_dir, 'outcome_model.pkl')):
                self.outcome_model = joblib.load(os.path.join(model_dir, 'outcome_model.pkl'))
            
            if os.path.exists(os.path.join(model_dir, 'feature_columns.txt')):
                with open(os.path.join(model_dir, 'feature_columns.txt'), 'r') as f:
                    self.feature_columns = f.read().strip().split('\n')
            
            print("ML models loaded successfully")
        except Exception as e:
            print(f"Error loading ML models: {e}")
            self.price_model = None
            self.outcome_model = None
    
    def get_customer_rating(self, user_id):
        """Calculate customer rating based on purchase and negotiation history"""
        try:
            # Get customer's order history
            orders = Order.query.filter_by(user_id=user_id).all()
            successful_orders = [o for o in orders if o.status == 'paid']
            
            # Get customer's negotiation history
            negotiations = Negotiation.query.filter_by(user_id=user_id).all()
            successful_negotiations = [n for n in negotiations if n.status == 'accepted']
            
            # Calculate rating based on:
            # 1. Purchase completion rate (50% weight)
            # 2. Negotiation success rate (30% weight)
            # 3. Total purchase value (20% weight)
            
            purchase_completion_rate = len(successful_orders) / max(len(orders), 1)
            negotiation_success_rate = len(successful_negotiations) / max(len(negotiations), 1)
            
            # Calculate average order value (normalized)
            total_value = sum(float(o.price) for o in successful_orders)
            avg_order_value = total_value / max(len(successful_orders), 1)
            value_score = min(avg_order_value / 50000, 1.0)  # Normalize to 0-1, cap at $50k
            
            # Calculate final rating (3.0 to 5.0 scale)
            base_rating = 3.0
            rating = base_rating + (
                purchase_completion_rate * 1.0 +  # 0-1.0 points
                negotiation_success_rate * 0.6 +  # 0-0.6 points
                value_score * 0.4  # 0-0.4 points
            )
            
            return min(rating, 5.0)
            
        except Exception as e:
            print(f"Error calculating customer rating: {e}")
            return 3.5  # Default rating
    
    def get_customer_history(self, user_id):
        """Get customer purchase and negotiation history"""
        try:
            orders = Order.query.filter_by(user_id=user_id).all()
            negotiations = Negotiation.query.filter_by(user_id=user_id).all()
            
            return {
                'purchase_history': len([o for o in orders if o.status == 'paid']),
                'negotiation_history': len(negotiations),
                'total_spent': sum(float(o.price) for o in orders if o.status == 'paid')
            }
        except Exception as e:
            print(f"Error getting customer history: {e}")
            return {'purchase_history': 0, 'negotiation_history': 0, 'total_spent': 0}
    
    def get_vehicle_market_data(self, vehicle_id):
        """Get market data for a vehicle"""
        try:
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return {}
            
            # Calculate days on market
            days_on_market = (datetime.utcnow() - vehicle.created_at).days
            
            # Get category score (simplified - in real system, use actual market data)
            category_scores = {
                'Sedan': 0.8,
                'SUV': 0.9,
                'Hatchback': 0.7,
                'Coupe': 0.6,
                'Convertible': 0.5,
                'Truck': 0.8,
                'Van': 0.6,
                'Wagon': 0.7
            }
            
            category_score = category_scores.get(vehicle.body_type, 0.7)
            
            # Market demand (simplified - in real system, use actual market data)
            market_demand = 0.7  # Default moderate demand
            
            # Seasonal factor (simplified)
            current_month = datetime.now().month
            seasonal_factors = {
                1: 0.9, 2: 0.9, 3: 1.0, 4: 1.1, 5: 1.1, 6: 1.0,
                7: 0.9, 8: 0.9, 9: 1.0, 10: 1.0, 11: 0.9, 12: 0.9
            }
            seasonal_factor = seasonal_factors.get(current_month, 1.0)
            
            return {
                'category_score': category_score,
                'market_demand': market_demand,
                'seasonal_factor': seasonal_factor,
                'days_on_market': days_on_market
            }
            
        except Exception as e:
            print(f"Error getting vehicle market data: {e}")
            return {
                'category_score': 0.7,
                'market_demand': 0.7,
                'seasonal_factor': 1.0,
                'days_on_market': 30
            }
    
    def predict_negotiation_outcome(self, user_id, vehicle_id, offer_amount):
        """Predict negotiation outcome using ML model"""
        if not self.price_model or not self.outcome_model:
            return self._fallback_prediction(vehicle_id, offer_amount)
        
        try:
            # Get vehicle data
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return None
            
            # Get customer data
            customer_rating = self.get_customer_rating(user_id)
            customer_history = self.get_customer_history(user_id)
            market_data = self.get_vehicle_market_data(vehicle_id)
            
            # Prepare features
            features = {
                'vehicle_price': float(vehicle.price),
                'vehicle_year': vehicle.year,
                'vehicle_mileage': vehicle.mileage,
                'vehicle_age': 2024 - vehicle.year,
                'customer_rating': customer_rating,
                'customer_purchase_history': customer_history['purchase_history'],
                'customer_negotiation_history': customer_history['negotiation_history'],
                'offer_amount': float(offer_amount),
                'offer_percentage': (float(offer_amount) / float(vehicle.price)) * 100,
                'vehicle_category_score': market_data['category_score'],
                'market_demand_score': market_data['market_demand'],
                'seasonal_factor': market_data['seasonal_factor'],
                'days_on_market': market_data['days_on_market']
            }
            
            # Convert to DataFrame
            X = pd.DataFrame([features])
            
            # Make predictions
            predicted_price = self.price_model.predict(X)[0]
            predicted_outcome = self.outcome_model.predict(X)[0]
            outcome_probabilities = self.outcome_model.predict_proba(X)[0]
            outcome_classes = self.outcome_model.classes_
            
            # Get probability for predicted outcome
            outcome_prob = outcome_probabilities[np.where(outcome_classes == predicted_outcome)[0][0]]
            
            return {
                'predicted_price': predicted_price,
                'predicted_outcome': predicted_outcome,
                'outcome_probability': outcome_prob,
                'all_outcome_probabilities': dict(zip(outcome_classes, outcome_probabilities)),
                'customer_rating': customer_rating,
                'market_data': market_data
            }
            
        except Exception as e:
            print(f"Error in ML prediction: {e}")
            return self._fallback_prediction(vehicle_id, offer_amount)
    
    def _fallback_prediction(self, vehicle_id, offer_amount):
        """Fallback prediction when ML model is not available"""
        try:
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return None
            
            vehicle_price = float(vehicle.price)
            offer_ratio = float(offer_amount) / vehicle_price
            
            # Simple business logic
            if offer_ratio >= 0.95:
                return {
                    'predicted_price': float(offer_amount),
                    'predicted_outcome': 'accepted_customer_offer',
                    'outcome_probability': 0.8,
                    'customer_rating': 4.0,
                    'market_data': {}
                }
            elif offer_ratio >= 0.85:
                suggested_price = vehicle_price * 0.92  # 8% discount
                return {
                    'predicted_price': suggested_price,
                    'predicted_outcome': 'counter_offer',
                    'outcome_probability': 0.7,
                    'customer_rating': 4.0,
                    'market_data': {}
                }
            else:
                return {
                    'predicted_price': vehicle_price * 0.90,  # 10% discount
                    'predicted_outcome': 'suggested_price',
                    'outcome_probability': 0.6,
                    'customer_rating': 4.0,
                    'market_data': {}
                }
                
        except Exception as e:
            print(f"Error in fallback prediction: {e}")
            return None
    
    def generate_ai_counter_offer(self, user_id, vehicle_id, customer_offer):
        """Generate AI counter offer based on ML prediction"""
        prediction = self.predict_negotiation_outcome(user_id, vehicle_id, customer_offer)
        
        if not prediction:
            return None
        
        vehicle = Vehicle.query.get(vehicle_id)
        vehicle_price = float(vehicle.price)
        
        # Generate counter offer based on prediction
        if prediction['predicted_outcome'] == 'accepted_customer_offer':
            return {
                'type': 'accept',
                'price': float(customer_offer),
                'message': f"Great offer! We accept your price of ${customer_offer:,.2f}.",
                'confidence': prediction['outcome_probability']
            }
        elif prediction['predicted_outcome'] == 'counter_offer':
            counter_price = prediction['predicted_price']
            return {
                'type': 'counter',
                'price': counter_price,
                'message': f"Thank you for your offer. We can do ${counter_price:,.2f} - that's a {((vehicle_price - counter_price) / vehicle_price * 100):.1f}% discount!",
                'confidence': prediction['outcome_probability']
            }
        elif prediction['predicted_outcome'] == 'suggested_price':
            suggested_price = prediction['predicted_price']
            return {
                'type': 'suggest',
                'price': suggested_price,
                'message': f"Based on market conditions and your customer rating, we suggest ${suggested_price:,.2f} - that's a {((vehicle_price - suggested_price) / vehicle_price * 100):.1f}% discount!",
                'confidence': prediction['outcome_probability']
            }
        else:  # rejected
            return {
                'type': 'reject',
                'price': vehicle_price,
                'message': f"Unfortunately, we cannot accept that offer. The best price we can offer is ${vehicle_price:,.2f}.",
                'confidence': prediction['outcome_probability']
            }

# Global instance
ml_engine = MLNegotiationEngine()
