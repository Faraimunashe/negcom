from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import datetime
from app import db
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.Integer, nullable=False)  # 1 for admin, 2 for User
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, email, password, name, role):
        self.email = email
        self.password = password
        self.name = name
        self.role = role
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)  # YEAR type
    mileage = db.Column(db.Integer, nullable=False)  # kilometers
    engine_type = db.Column(db.String(80), nullable=False)  # petrol, diesel
    transmission = db.Column(db.String(80), nullable=False)  # AUTO, MANUAL
    body_type = db.Column(db.String(80), nullable=False)  # Sedan, SUV, Truck, etc.
    color = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # eg 12000.50
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, make, model, year, mileage, engine_type, transmission, body_type, color, price):
        self.make = make
        self.model = model
        self.year = year
        self.mileage = mileage
        self.engine_type = engine_type
        self.transmission = transmission
        self.body_type = body_type
        self.color = color
        self.price = price
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class VehicleImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    image_url = db.Column(db.String(80), nullable=False)  # eg images/v0212.jpg
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, vehicle_id, image_url, is_primary):
        self.vehicle_id = vehicle_id
        self.image_url = image_url
        self.is_primary = is_primary
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(300), nullable=False)

    def __init__(self, name, description):
        self.name = name
        self.description = description

class VehicleCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __init__(self, vehicle_id, category_id):
        self.vehicle_id = vehicle_id
        self.category_id = category_id

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(80), nullable=False)  # pending, paid, failed, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vehicle = db.relationship('Vehicle', backref='orders')
    user = db.relationship('User', backref='orders')

    def __init__(self, user_id, vehicle_id, price, status):
        self.user_id = user_id
        self.vehicle_id = vehicle_id
        self.price = price
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(80), nullable=False)  # Credit Card, PayPal, Bank Transfer, Mobile Money, etc.
    reference = db.Column(db.String(80), unique=True, nullable=False)
    status = db.Column(db.String(80), nullable=False)  # success, failed, pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, order_id, amount, method, reference, status):
        self.order_id = order_id
        self.amount = amount
        self.method = method
        self.reference = reference
        self.status = status
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Negotiation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    status = db.Column(db.String(80), nullable=False)  # ongoing, accepted, rejected, expired
    final_price = db.Column(db.Numeric(10, 2), nullable=True)  # nullable until accepted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vehicle = db.relationship('Vehicle', backref='negotiations')
    user = db.relationship('User', backref='negotiations')

    def __init__(self, user_id, vehicle_id, status, final_price=None):
        self.user_id = user_id
        self.vehicle_id = vehicle_id
        self.status = status
        self.final_price = final_price
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class OfferByEnum(Enum):
    BUYER = "BUYER"
    AI = "AI"

class NegotiationOffer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    negotiation_id = db.Column(db.Integer, db.ForeignKey('negotiation.id'), nullable=False)
    offer_by = db.Column(db.Enum(OfferByEnum), nullable=False)  # BUYER, AI
    offer_price = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.String(200), nullable=True)  # optional: e.g. "customer loyalty discount", "AI counter-offer"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, negotiation_id, offer_by, offer_price, reason=None):
        self.negotiation_id = negotiation_id
        self.offer_by = offer_by
        self.offer_price = offer_price
        self.reason = reason
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class DiscountRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    max_discount_percentage = db.Column(db.Numeric(5, 2), nullable=False)  # from 0.01 to 99.99
    min_price_allowed = db.Column(db.Numeric(10, 2), nullable=False)

    def __init__(self, vehicle_id, max_discount_percentage, min_price_allowed):
        self.vehicle_id = vehicle_id
        self.max_discount_percentage = max_discount_percentage
        self.min_price_allowed = min_price_allowed

class CustomerHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_purchases = db.Column(db.Integer, nullable=False)  # count of completed purchases
    total_spent = db.Column(db.Numeric(10, 2), nullable=False)  # lifetime value
    avg_rating = db.Column(db.Numeric(3, 2), nullable=False)  # from reviews
    last_purchase_date = db.Column(db.DateTime, nullable=True)

    def __init__(self, user_id, total_purchases, total_spent, avg_rating, last_purchase_date=None):
        self.user_id = user_id
        self.total_purchases = total_purchases
        self.total_spent = total_spent
        self.avg_rating = avg_rating
        self.last_purchase_date = last_purchase_date

class CustomerRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    avg_rating = db.Column(db.Integer, nullable=False)  # 1 - 5
    reason = db.Column(db.String(200), nullable=False)  # loyalty, late payments, negotiation behaviour, etc
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, avg_rating, reason):
        self.user_id = user_id
        self.avg_rating = avg_rating
        self.reason = reason
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Review(db.Model):  # this one is for users to rate the platform
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 - 5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, message, rating):
        self.user_id = user_id
        self.message = message
        self.rating = rating
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # info, success, warning, error
    category = db.Column(db.String(50), nullable=False)  # order, negotiation, system
    is_read = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(200), nullable=True)  # Link to relevant page
    related_id = db.Column(db.Integer, nullable=True)  # ID of related object
    related_type = db.Column(db.String(50), nullable=True)  # order, negotiation, vehicle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')

    def __init__(self, user_id, title, message, type='info', category='system', 
                 action_url=None, related_id=None, related_type=None):
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type
        self.category = category
        self.action_url = action_url
        self.related_id = related_id
        self.related_type = related_type
        self.is_read = False
        self.created_at = datetime.utcnow()

