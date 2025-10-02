# Admin Blueprint
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Vehicle, VehicleImage, Order, Payment, Negotiation, NegotiationOffer, Category, VehicleCategory, Review
from app import db
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import json
import os
import uuid
from werkzeug.utils import secure_filename

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

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_vehicle_images(vehicle_id, files):
    """Save uploaded images for a vehicle"""
    if not files or not files[0].filename:
        return []
    
    saved_images = []
    upload_folder = os.path.join(current_app.root_path, 'static', 'images', 'vehicles')
    
    # Create vehicle-specific folder
    vehicle_folder = os.path.join(upload_folder, str(vehicle_id))
    os.makedirs(vehicle_folder, exist_ok=True)
    
    for i, file in enumerate(files):
        if file and allowed_file(file.filename):
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Save file
            file_path = os.path.join(vehicle_folder, unique_filename)
            file.save(file_path)
            
            # Create relative path for database
            relative_path = f"images/vehicles/{vehicle_id}/{unique_filename}"
            
            # Create VehicleImage record
            is_primary = (i == 0)  # First image is primary
            vehicle_image = VehicleImage(
                vehicle_id=vehicle_id,
                image_url=relative_path,
                is_primary=is_primary
            )
            db.session.add(vehicle_image)
            saved_images.append(vehicle_image)
    
    return saved_images

def delete_vehicle_images(vehicle_id):
    """Delete all images for a vehicle"""
    # Get all images for the vehicle
    images = VehicleImage.query.filter_by(vehicle_id=vehicle_id).all()
    
    for image in images:
        # Delete physical file
        file_path = os.path.join(current_app.root_path, 'static', image.image_url)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete database record
        db.session.delete(image)
    
    # Remove vehicle folder if empty
    vehicle_folder = os.path.join(current_app.root_path, 'static', 'images', 'vehicles', str(vehicle_id))
    if os.path.exists(vehicle_folder) and not os.listdir(vehicle_folder):
        os.rmdir(vehicle_folder)

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
    from app.forms import AdminVehicleEditForm
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    form = AdminVehicleEditForm(obj=vehicle)
    
    if form.validate_on_submit():
        try:
            # Update vehicle details
            vehicle.make = form.make.data
            vehicle.model = form.model.data
            vehicle.year = form.year.data
            vehicle.mileage = form.mileage.data
            vehicle.engine_type = form.engine_type.data
            vehicle.transmission = form.transmission.data
            vehicle.body_type = form.body_type.data
            vehicle.color = form.color.data
            vehicle.price = form.price.data
            
            # Handle additional images if uploaded
            if form.additional_images.data and form.additional_images.data[0].filename:
                saved_images = save_vehicle_images(vehicle_id, form.additional_images.data)
                if saved_images:
                    flash(f'Added {len(saved_images)} additional images!', 'success')
            
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
    
    try:
        # Delete associated images (both files and database records)
        delete_vehicle_images(vehicle_id)
        
        # Delete the vehicle
        db.session.delete(vehicle)
        db.session.commit()
        
        flash('Vehicle and all associated images deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting vehicle: {str(e)}', 'error')
    
    return redirect(url_for('admin.vehicles'))

@admin_bp.route('/vehicles/<int:vehicle_id>/images/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vehicle_image(vehicle_id, image_id):
    """Delete a specific vehicle image"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    image = VehicleImage.query.filter_by(id=image_id, vehicle_id=vehicle_id).first_or_404()
    
    try:
        # Delete physical file
        file_path = os.path.join(current_app.root_path, 'static', image.image_url)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete database record
        db.session.delete(image)
        db.session.commit()
        
        flash('Image deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting image: {str(e)}', 'error')
    
    return redirect(url_for('admin.vehicle_detail', vehicle_id=vehicle_id))

@admin_bp.route('/vehicles/<int:vehicle_id>/images/<int:image_id>/set-primary', methods=['POST'])
@login_required
@admin_required
def set_primary_image(vehicle_id, image_id):
    """Set an image as the primary image for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    image = VehicleImage.query.filter_by(id=image_id, vehicle_id=vehicle_id).first_or_404()
    
    try:
        # Remove primary flag from all images of this vehicle
        VehicleImage.query.filter_by(vehicle_id=vehicle_id).update({'is_primary': False})
        
        # Set this image as primary
        image.is_primary = True
        
        db.session.commit()
        flash('Primary image updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating primary image: {str(e)}', 'error')
    
    return redirect(url_for('admin.vehicle_detail', vehicle_id=vehicle_id))

@admin_bp.route('/vehicles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_vehicle():
    """Create new vehicle"""
    from app.forms import AdminVehicleForm
    form = AdminVehicleForm()
    
    if form.validate_on_submit():
        try:
            # Create the vehicle first
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
            db.session.flush()  # Get the vehicle ID without committing
            
            # Save uploaded images
            if form.images.data:
                saved_images = save_vehicle_images(new_vehicle.id, form.images.data)
                if not saved_images:
                    flash('No valid images were uploaded!', 'error')
                    db.session.rollback()
                    return render_template('admin/vehicles/create.html', form=form)
            
            db.session.commit()
            flash('Vehicle created successfully with images!', 'success')
            return redirect(url_for('admin.vehicle_detail', vehicle_id=new_vehicle.id))
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
    search_query = request.args.get('search', '')
    payment_filter = request.args.get('payment', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    query = Order.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    if search_query:
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
    
    if payment_filter:
        if payment_filter == 'paid':
            query = query.filter(Order.status == 'paid')
        elif payment_filter == 'pending':
            query = query.filter(Order.status == 'pending')
        elif payment_filter == 'failed':
            query = query.filter(Order.status == 'failed')
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Order.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Order.created_at <= to_date)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price':
        order_column = Order.price
    elif sort_by == 'created_at':
        order_column = Order.created_at
    else:
        order_column = Order.created_at
    
    if sort_order == 'asc':
        query = query.order_by(order_column)
    else:
        query = query.order_by(desc(order_column))
    
    orders = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate statistics for the template
    total_orders = Order.query.count()
    paid_orders = Order.query.filter(Order.status == 'paid').count()
    pending_orders = Order.query.filter(Order.status == 'pending').count()
    total_revenue = db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0
    
    return render_template('admin/orders/list.html', 
                         orders=orders, 
                         status_filter=status_filter,
                         search_query=search_query,
                         payment_filter=payment_filter,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_orders=total_orders,
                         paid_orders=paid_orders,
                         pending_orders=pending_orders,
                         total_revenue=float(total_revenue))

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
    search_query = request.args.get('search', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    query = Negotiation.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Negotiation.status == status_filter)
    
    if search_query:
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Negotiation.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Negotiation.created_at <= to_date)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'final_price':
        # For negotiations, we might want to sort by the final agreed price
        # For now, we'll sort by created_at as negotiations don't have a direct price field
        order_column = Negotiation.created_at
    elif sort_by == 'created_at':
        order_column = Negotiation.created_at
    else:
        order_column = Negotiation.created_at
    
    if sort_order == 'asc':
        query = query.order_by(order_column)
    else:
        query = query.order_by(desc(order_column))
    
    negotiations = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate statistics for the template
    total_negotiations = Negotiation.query.count()
    active_negotiations = Negotiation.query.filter(Negotiation.status == 'ongoing').count()
    successful_negotiations = Negotiation.query.filter(Negotiation.status == 'accepted').count()
    
    # Calculate average negotiation value (from associated orders)
    avg_negotiation_value = db.session.query(func.avg(Order.price)).join(
        Negotiation, Order.vehicle_id == Negotiation.vehicle_id
    ).filter(Negotiation.status == 'accepted').scalar() or 0
    
    return render_template('admin/negotiations/list.html', 
                         negotiations=negotiations, 
                         status_filter=status_filter,
                         search_query=search_query,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_negotiations=total_negotiations,
                         active_negotiations=active_negotiations,
                         successful_negotiations=successful_negotiations,
                         avg_negotiation_value=float(avg_negotiation_value))

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

@admin_bp.route('/users/analytics')
@login_required
@admin_required
def user_analytics():
    """User analytics and reports"""
    
    # User registration trends
    user_activity = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('new_users')
    ).filter(User.created_at >= datetime.utcnow() - timedelta(days=90)).group_by(
        func.date(User.created_at)
    ).order_by('date').all()
    
    # User role distribution
    role_distribution = db.session.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    
    # Top users by activity (orders + negotiations)
    top_active_users = db.session.query(
        User.name,
        User.email,
        func.count(Order.id).label('orders'),
        func.count(Negotiation.id).label('negotiations'),
        func.sum(Order.price).label('total_spent')
    ).outerjoin(Order, User.id == Order.user_id).outerjoin(
        Negotiation, User.id == Negotiation.user_id
    ).group_by(User.id, User.name, User.email).order_by(
        desc(func.count(Order.id) + func.count(Negotiation.id))
    ).limit(10).all()
    
    # Recent user registrations
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    return render_template('admin/users/analytics.html',
                         user_activity=user_activity,
                         role_distribution=role_distribution,
                         top_active_users=top_active_users,
                         recent_users=recent_users)

@admin_bp.route('/negotiations/analytics')
@login_required
@admin_required
def negotiation_analytics():
    """Negotiation analytics and reports"""
    
    # Monthly success data
    monthly_success = db.session.query(
        func.extract('year', Negotiation.created_at).label('year'),
        func.extract('month', Negotiation.created_at).label('month'),
        func.count(Negotiation.id).label('total'),
        func.sum(func.case([(Negotiation.status == 'accepted', 1)], else_=0)).label('accepted')
    ).group_by(
        func.extract('year', Negotiation.created_at),
        func.extract('month', Negotiation.created_at)
    ).order_by('year', 'month').all()
    
    # Format month data for template
    formatted_monthly_success = []
    for data in monthly_success:
        month_name = datetime(int(data.year), int(data.month), 1).strftime('%B %Y')
        formatted_monthly_success.append({
            'month': month_name,
            'total': int(data.total or 0),
            'accepted': int(data.accepted or 0)
        })
    
    # Daily negotiations for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_negotiations = db.session.query(
        func.date(Negotiation.created_at).label('date'),
        func.count(Negotiation.id).label('negotiations')
    ).filter(
        Negotiation.created_at >= thirty_days_ago
    ).group_by(func.date(Negotiation.created_at)).order_by('date').all()
    
    # Negotiation status distribution
    status_distribution = db.session.query(
        Negotiation.status,
        func.count(Negotiation.id).label('count')
    ).group_by(Negotiation.status).all()
    
    # Top vehicles by negotiations
    top_vehicles = db.session.query(
        Vehicle.make,
        Vehicle.model,
        func.count(Negotiation.id).label('negotiations'),
        func.sum(func.case([(Negotiation.status == 'accepted', 1)], else_=0)).label('accepted')
    ).join(Negotiation, Vehicle.id == Negotiation.vehicle_id).group_by(
        Vehicle.make, Vehicle.model
    ).order_by(desc('negotiations')).limit(10).all()
    
    # Top users by negotiations
    top_users = db.session.query(
        User.name,
        func.count(Negotiation.id).label('negotiations'),
        func.sum(func.case([(Negotiation.status == 'accepted', 1)], else_=0)).label('accepted')
    ).join(Negotiation, User.id == Negotiation.user_id).group_by(
        User.id, User.name
    ).order_by(desc('negotiations')).limit(10).all()
    
    return render_template('admin/negotiations/analytics.html',
                         monthly_success=formatted_monthly_success,
                         daily_negotiations=daily_negotiations,
                         status_distribution=status_distribution,
                         top_vehicles=top_vehicles,
                         top_users=top_users)

@admin_bp.route('/orders/analytics')
@login_required
@admin_required
def order_analytics():
    """Order analytics and reports"""
    
    # Monthly revenue data
    monthly_revenue = db.session.query(
        func.extract('year', Order.created_at).label('year'),
        func.extract('month', Order.created_at).label('month'),
        func.sum(Order.price).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(Order.status == 'paid').group_by(
        func.extract('year', Order.created_at),
        func.extract('month', Order.created_at)
    ).order_by('year', 'month').all()
    
    # Format month data for template
    formatted_monthly_revenue = []
    for data in monthly_revenue:
        month_name = datetime(int(data.year), int(data.month), 1).strftime('%B %Y')
        formatted_monthly_revenue.append({
            'month': month_name,
            'revenue': float(data.revenue or 0),
            'orders': int(data.orders or 0)
        })
    
    # Daily sales for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('orders')
    ).filter(
        Order.created_at >= thirty_days_ago,
        Order.status == 'paid'
    ).group_by(func.date(Order.created_at)).order_by('date').all()
    
    # Order status distribution
    status_distribution = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    
    # Top selling vehicles
    top_vehicles = db.session.query(
        Vehicle.make,
        Vehicle.model,
        func.count(Order.id).label('sales'),
        func.sum(Order.price).label('revenue')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.make, Vehicle.model).order_by(desc('revenue')).limit(10).all()
    
    # Top customers
    top_customers = db.session.query(
        User.name,
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('total_spent')
    ).join(Order, User.id == Order.user_id).filter(
        Order.status == 'paid'
    ).group_by(User.id, User.name).order_by(desc('total_spent')).limit(10).all()
    
    return render_template('admin/orders/analytics.html',
                         monthly_revenue=formatted_monthly_revenue,
                         daily_sales=daily_sales,
                         status_distribution=status_distribution,
                         top_vehicles=top_vehicles,
                         top_customers=top_customers)

@admin_bp.route('/orders/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_order_actions():
    """Handle bulk order actions"""
    action = request.form.get('action')
    order_ids = request.form.getlist('order_ids')
    
    if not order_ids:
        flash('No orders selected!', 'error')
        return redirect(url_for('admin.orders'))
    
    try:
        orders = Order.query.filter(Order.id.in_(order_ids)).all()
        
        if action == 'mark_paid':
            for order in orders:
                order.status = 'paid'
            flash(f'{len(orders)} orders marked as paid!', 'success')
        elif action == 'mark_shipped':
            for order in orders:
                order.status = 'shipped'
            flash(f'{len(orders)} orders marked as shipped!', 'success')
        elif action == 'mark_delivered':
            for order in orders:
                order.status = 'delivered'
            flash(f'{len(orders)} orders marked as delivered!', 'success')
        elif action == 'cancel':
            for order in orders:
                order.status = 'cancelled'
            flash(f'{len(orders)} orders cancelled!', 'success')
        else:
            flash('Invalid action!', 'error')
            return redirect(url_for('admin.orders'))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing bulk action: {str(e)}', 'error')
    
    return redirect(url_for('admin.orders'))

@admin_bp.route('/negotiations/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_negotiation_actions():
    """Handle bulk negotiation actions"""
    action = request.form.get('action')
    negotiation_ids = request.form.getlist('negotiation_ids')
    
    if not negotiation_ids:
        flash('No negotiations selected!', 'error')
        return redirect(url_for('admin.negotiations'))
    
    try:
        negotiations = Negotiation.query.filter(Negotiation.id.in_(negotiation_ids)).all()
        
        if action == 'accept':
            for negotiation in negotiations:
                negotiation.status = 'accepted'
            flash(f'{len(negotiations)} negotiations accepted!', 'success')
        elif action == 'reject':
            for negotiation in negotiations:
                negotiation.status = 'rejected'
            flash(f'{len(negotiations)} negotiations rejected!', 'success')
        elif action == 'close':
            for negotiation in negotiations:
                negotiation.status = 'closed'
            flash(f'{len(negotiations)} negotiations closed!', 'success')
        else:
            flash('Invalid action!', 'error')
            return redirect(url_for('admin.negotiations'))
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing bulk action: {str(e)}', 'error')
    
    return redirect(url_for('admin.negotiations'))

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

@admin_bp.route('/negotiations/<int:negotiation_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_negotiation_status(negotiation_id):
    """Update negotiation status"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    new_status = request.form.get('status')
    if new_status not in ['ongoing', 'accepted', 'rejected', 'expired']:
        flash('Invalid status!', 'error')
        return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))
    
    try:
        negotiation.status = new_status
        negotiation.updated_at = datetime.utcnow()
        
        # If accepting, set final price from latest offer
        if new_status == 'accepted':
            latest_offer = NegotiationOffer.query.filter_by(
                negotiation_id=negotiation_id
            ).order_by(desc(NegotiationOffer.created_at)).first()
            
            if latest_offer:
                negotiation.final_price = latest_offer.offer_price
        
        db.session.commit()
        flash(f'Negotiation status updated to {new_status}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating negotiation status.', 'error')
    
    return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/offers/<int:offer_id>/accept', methods=['POST'])
@login_required
@admin_required
def accept_negotiation_offer(negotiation_id, offer_id):
    """Accept a specific negotiation offer"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    offer = NegotiationOffer.query.get_or_404(offer_id)
    
    if offer.negotiation_id != negotiation_id:
        flash('Invalid offer for this negotiation!', 'error')
        return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))
    
    try:
        negotiation.status = 'accepted'
        negotiation.final_price = offer.offer_price
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Offer of ${offer.offer_price:,.2f} accepted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while accepting the offer.', 'error')
    
    return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/offers/<int:offer_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_negotiation_offer(negotiation_id, offer_id):
    """Reject a specific negotiation offer"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    offer = NegotiationOffer.query.get_or_404(offer_id)
    
    if offer.negotiation_id != negotiation_id:
        flash('Invalid offer for this negotiation!', 'error')
        return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))
    
    try:
        # Create AI counter offer
        ai_response = ml_engine.generate_ai_counter_offer(
            negotiation.user_id, negotiation.vehicle_id, float(offer.offer_price)
        )
        
        if ai_response and ai_response['type'] in ['counter', 'suggest']:
            # Create AI counter offer
            ai_offer = NegotiationOffer(
                negotiation_id=negotiation_id,
                offer_by=OfferByEnum.AI,
                offer_price=ai_response['price'],
                reason=f"Counter offer: {ai_response['message']}"
            )
            db.session.add(ai_offer)
            negotiation.status = 'ongoing'
        else:
            negotiation.status = 'rejected'
        
        negotiation.updated_at = datetime.utcnow()
        db.session.commit()
        
        if ai_response and ai_response['type'] in ['counter', 'suggest']:
            flash(f'Offer rejected. AI counter offer of ${ai_response["price"]:,.2f} made.', 'info')
        else:
            flash('Offer rejected successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while rejecting the offer.', 'error')
    
    return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/make-offer', methods=['POST'])
@login_required
@admin_required
def make_negotiation_offer(negotiation_id):
    """Make a counter offer as admin"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    offer_price = request.form.get('offer_price', type=float)
    reason = request.form.get('reason', '')
    
    if not offer_price or offer_price <= 0:
        flash('Invalid offer price!', 'error')
        return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))
    
    try:
        # Create admin counter offer
        admin_offer = NegotiationOffer(
            negotiation_id=negotiation_id,
            offer_by=OfferByEnum.AI,  # Using AI enum for admin offers
            offer_price=offer_price,
            reason=f"Admin counter offer: {reason}" if reason else "Admin counter offer"
        )
        db.session.add(admin_offer)
        
        negotiation.status = 'ongoing'
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Counter offer of ${offer_price:,.2f} made successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while making the counter offer.', 'error')
    
    return redirect(url_for('admin.negotiation_detail', negotiation_id=negotiation_id))