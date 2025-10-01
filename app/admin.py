# Admin Blueprint
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, Vehicle, VehicleImage, Order, Payment, Negotiation, NegotiationOffer, Category, VehicleCategory, Review
from app import db
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 1:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with statistics and overview"""
    
    # Calculate statistics
    total_vehicles = Vehicle.query.count()
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_negotiations = Negotiation.query.count()
    
    # Calculate revenue from completed orders
    revenue = db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0
    
    # Recent activity
    recent_orders = Order.query.order_by(desc(Order.created_at)).limit(5).all()
    recent_negotiations = Negotiation.query.order_by(desc(Negotiation.created_at)).limit(5).all()
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_vehicles=total_vehicles,
                         total_users=total_users,
                         total_orders=total_orders,
                         total_negotiations=total_negotiations,
                         revenue=float(revenue),
                         recent_orders=recent_orders,
                         recent_negotiations=recent_negotiations,
                         recent_users=recent_users)

@admin_bp.route('/vehicles')
@login_required
@admin_required
def vehicles():
    """Admin vehicle management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Vehicle.query
    
    if search:
        query = query.filter(
            db.or_(
                Vehicle.make.ilike(f'%{search}%'),
                Vehicle.model.ilike(f'%{search}%'),
                Vehicle.body_type.ilike(f'%{search}%')
            )
        )
    
    vehicles = query.order_by(desc(Vehicle.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/vehicles/list.html', vehicles=vehicles, search=search)

@admin_bp.route('/vehicles/<int:vehicle_id>')
@login_required
@admin_required
def vehicle_detail(vehicle_id):
    """Admin vehicle detail view"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    images = VehicleImage.query.filter_by(vehicle_id=vehicle_id).all()
    orders = Order.query.filter_by(vehicle_id=vehicle_id).all()
    negotiations = Negotiation.query.filter_by(vehicle_id=vehicle_id).all()
    
    return render_template('admin/vehicles/detail.html',
                         vehicle=vehicle,
                         images=images,
                         orders=orders,
                         negotiations=negotiations)

@admin_bp.route('/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_vehicle(vehicle_id):
    """Edit vehicle details"""
    from app.forms import AdminVehicleForm
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = AdminVehicleForm(obj=vehicle)
    
    if form.validate_on_submit():
        try:
            vehicle.make = form.make.data
            vehicle.model = form.model.data
            vehicle.year = form.year.data
            vehicle.mileage = form.mileage.data
            vehicle.engine_type = form.engine_type.data
            vehicle.transmission = form.transmission.data
            vehicle.body_type = form.body_type.data
            vehicle.color = form.color.data
            vehicle.price = form.price.data
            
            db.session.commit()
            flash('Vehicle updated successfully!', 'success')
            return redirect(url_for('admin.vehicle_detail', vehicle_id=vehicle_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating vehicle: {str(e)}', 'error')
    
    return render_template('admin/vehicles/edit.html', vehicle=vehicle, form=form)

@admin_bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vehicle(vehicle_id):
    """Delete vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Delete associated images
    VehicleImage.query.filter_by(vehicle_id=vehicle_id).delete()
    
    # Delete the vehicle
    db.session.delete(vehicle)
    db.session.commit()
    
    flash('Vehicle deleted successfully!', 'success')
    return redirect(url_for('admin.vehicles'))

@admin_bp.route('/vehicles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_vehicle():
    """Create new vehicle"""
    from app.forms import AdminVehicleForm
    form = AdminVehicleForm()
    
    if form.validate_on_submit():
        try:
            new_vehicle = Vehicle(
                make=form.make.data,
                model=form.model.data,
                year=form.year.data,
                mileage=form.mileage.data,
                engine_type=form.engine_type.data,
                transmission=form.transmission.data,
                body_type=form.body_type.data,
                color=form.color.data,
                price=form.price.data
            )
            db.session.add(new_vehicle)
            db.session.commit()
            flash('Vehicle created successfully!', 'success')
            return redirect(url_for('admin.vehicles'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating vehicle: {str(e)}', 'error')
    
    return render_template('admin/vehicles/create.html', form=form)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin user management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    if role_filter:
        query = query.filter(User.role == int(role_filter))
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users/list.html', users=users, search=search, role_filter=role_filter)

@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    """Admin user detail view"""
    user = User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).all()
    negotiations = Negotiation.query.filter_by(user_id=user_id).all()
    reviews = Review.query.filter_by(user_id=user_id).all()
    
    # Calculate statistics
    total_spent = sum(order.price for order in orders if order.status == 'paid')
    total_orders = len(orders)
    total_negotiations = len(negotiations)
    total_reviews = len(reviews)
    successful_negotiations = len([n for n in negotiations if n.status == 'accepted'])
    
    # Calculate recent activity (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_orders = len([o for o in orders if o.created_at >= thirty_days_ago])
    recent_negotiations = len([n for n in negotiations if n.created_at >= thirty_days_ago])
    
    return render_template('admin/users/detail.html',
                         user=user,
                         orders=orders,
                         negotiations=negotiations,
                         reviews=reviews,
                         total_spent=total_spent,
                         total_orders=total_orders,
                         total_negotiations=total_negotiations,
                         total_reviews=total_reviews,
                         successful_negotiations=successful_negotiations,
                         recent_orders=recent_orders,
                         recent_negotiations=recent_negotiations)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    from app.forms import AdminUserForm
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            # Check if email is being changed and if it's already taken
            if form.email.data != user.email:
                existing_user = User.query.filter_by(email=form.email.data).first()
                if existing_user and existing_user.id != user.id:
                    flash('Email address is already in use!', 'error')
                    return render_template('admin/users/edit.html', user=user, form=form)
            
            user.name = form.name.data
            user.email = form.email.data
            user.role = form.role.data
            
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.user_detail', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/users/edit.html', user=user, form=form)

@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
@login_required
@admin_required
def toggle_user_role(user_id):
    """Toggle user role between admin and regular user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot change your own role!', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    user.role = 1 if user.role == 2 else 2
    db.session.commit()
    
    role_text = 'Admin' if user.role == 1 else 'User'
    flash(f'User role changed to {role_text}!', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    # Delete related data first (orders, negotiations, etc.)
    # Note: You might want to add cascade deletes in your models
    Order.query.filter_by(user_id=user_id).delete()
    Negotiation.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.name} has been deleted successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """Admin order management"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Order.query
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    orders = query.order_by(desc(Order.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/orders/list.html', orders=orders, status_filter=status_filter)

@admin_bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """Admin order detail view"""
    order = Order.query.get_or_404(order_id)
    payment = Payment.query.filter_by(order_id=order_id).first()
    user = User.query.get(order.user_id)
    vehicle = Vehicle.query.get(order.vehicle_id)
    
    return render_template('admin/orders/detail.html',
                         order=order,
                         payment=payment,
                         user=user,
                         vehicle=vehicle)

@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    """Update order status"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'paid', 'failed', 'refunded']:
        order.status = new_status
        db.session.commit()
        flash(f'Order status updated to {new_status}!', 'success')
    else:
        flash('Invalid status!', 'error')
    
    return redirect(url_for('admin.order_detail', order_id=order_id))

@admin_bp.route('/negotiations')
@login_required
@admin_required
def negotiations():
    """Admin negotiation management"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Negotiation.query
    
    if status_filter:
        query = query.filter(Negotiation.status == status_filter)
    
    negotiations = query.order_by(desc(Negotiation.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/negotiations/list.html', negotiations=negotiations, status_filter=status_filter)

@admin_bp.route('/negotiations/<int:negotiation_id>')
@login_required
@admin_required
def negotiation_detail(negotiation_id):
    """Admin negotiation detail view"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    offers = NegotiationOffer.query.filter_by(negotiation_id=negotiation_id).order_by(NegotiationOffer.created_at).all()
    user = User.query.get(negotiation.user_id)
    vehicle = Vehicle.query.get(negotiation.vehicle_id)
    
    return render_template('admin/negotiations/detail.html',
                         negotiation=negotiation,
                         offers=offers,
                         user=user,
                         vehicle=vehicle)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Admin reports and analytics"""
    
    # Monthly revenue
    monthly_revenue = db.session.query(
        func.extract('year', Order.created_at).label('year'),
        func.extract('month', Order.created_at).label('month'),
        func.sum(Order.price).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(Order.status == 'paid').group_by(
        func.extract('year', Order.created_at),
        func.extract('month', Order.created_at)
    ).order_by('year', 'month').all()
    
    # Vehicle performance
    vehicle_performance = db.session.query(
        Vehicle.make,
        Vehicle.model,
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue'),
        func.avg(Order.price).label('avg_price')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.make, Vehicle.model).order_by(desc('revenue')).limit(10).all()
    
    # User activity
    user_activity = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('new_users')
    ).filter(User.created_at >= datetime.utcnow() - timedelta(days=90)).group_by(
        func.date(User.created_at)
    ).order_by('date').all()
    
    return render_template('admin/reports/dashboard.html',
                         monthly_revenue=monthly_revenue,
                         vehicle_performance=vehicle_performance,
                         user_activity=user_activity)

@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """API endpoint for dashboard statistics"""
    
    # Real-time stats
    stats = {
        'total_vehicles': Vehicle.query.count(),
        'total_users': User.query.count(),
        'total_orders': Order.query.count(),
        'total_negotiations': Negotiation.query.count(),
        'revenue': float(db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0),
        'pending_orders': Order.query.filter(Order.status == 'pending').count(),
        'active_negotiations': Negotiation.query.filter(Negotiation.status == 'ongoing').count(),
        'new_users_today': User.query.filter(User.created_at >= datetime.utcnow().date()).count()
    }
    
    return jsonify(stats)