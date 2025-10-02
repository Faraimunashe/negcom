from flask import Blueprint, render_template
from flask_login import login_required, current_user
from . import db
from app.models import User, Order, Negotiation, Vehicle
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Get customer statistics
    total_orders = Order.query.filter_by(user_id=current_user.id).count()
    paid_orders = Order.query.filter_by(user_id=current_user.id, status='paid').count()
    pending_orders = Order.query.filter_by(user_id=current_user.id, status='pending').count()
    
    total_negotiations = Negotiation.query.filter_by(user_id=current_user.id).count()
    active_negotiations = Negotiation.query.filter_by(user_id=current_user.id, status='ongoing').count()
    successful_negotiations = Negotiation.query.filter_by(user_id=current_user.id, status='accepted').count()
    
    # Calculate total spent
    total_spent = db.session.query(func.sum(Order.price)).filter_by(
        user_id=current_user.id, status='paid'
    ).scalar() or 0
    
    # Get recent orders (last 5)
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(
        desc(Order.created_at)
    ).limit(5).all()
    
    # Get recent negotiations (last 5)
    recent_negotiations = Negotiation.query.filter_by(user_id=current_user.id).order_by(
        desc(Negotiation.created_at)
    ).limit(5).all()
    
    # Get featured vehicles (random selection)
    featured_vehicles = Vehicle.query.order_by(
        func.random()
    ).limit(3).all()
    
    # Calculate customer rating (simplified)
    customer_rating = 4.5  # This could be calculated based on order history, negotiations, etc.
    
    # Get monthly stats
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.created_at >= thirty_days_ago
    ).count()
    
    monthly_negotiations = Negotiation.query.filter(
        Negotiation.user_id == current_user.id,
        Negotiation.created_at >= thirty_days_ago
    ).count()
    
    return render_template('dashboard.html',
                         total_orders=total_orders,
                         paid_orders=paid_orders,
                         pending_orders=pending_orders,
                         total_negotiations=total_negotiations,
                         active_negotiations=active_negotiations,
                         successful_negotiations=successful_negotiations,
                         total_spent=total_spent,
                         recent_orders=recent_orders,
                         recent_negotiations=recent_negotiations,
                         featured_vehicles=featured_vehicles,
                         customer_rating=customer_rating,
                         monthly_orders=monthly_orders,
                         monthly_negotiations=monthly_negotiations)
