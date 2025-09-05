from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc, asc, and_, or_, case
from datetime import datetime, timedelta
from app import db
from app.models import (
    User, Vehicle, VehicleImage, Category, VehicleCategory,
    Order, Payment, Negotiation, NegotiationOffer,
    CustomerHistory, CustomerRating, Review, DiscountRule
)
from app.forms import VehicleSearchForm, VehicleFilterForm
from functools import wraps

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to ensure only admins can access admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access admin panel.', 'error')
            return redirect(url_for('auth.login'))
        if current_user.role != 1:  # 1 = admin, 2 = user
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
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
    
    # Calculate revenue (from paid orders)
    total_revenue = db.session.query(func.sum(Order.price)).filter(
        Order.status == 'paid'
    ).scalar() or 0
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    recent_orders = Order.query.filter(
        Order.created_at >= week_ago
    ).order_by(desc(Order.created_at)).limit(5).all()
    
    recent_negotiations = Negotiation.query.filter(
        Negotiation.created_at >= week_ago
    ).order_by(desc(Negotiation.created_at)).limit(5).all()
    
    recent_users = User.query.filter(
        User.created_at >= week_ago
    ).order_by(desc(User.created_at)).limit(5).all()
    
    # Sales trends (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue')
    ).filter(
        and_(
            Order.created_at >= thirty_days_ago,
            Order.status == 'paid'
        )
    ).group_by(func.date(Order.created_at)).all()
    
    # Popular vehicles (most ordered)
    popular_vehicles = db.session.query(
        Vehicle.make,
        Vehicle.model,
        func.count(Order.id).label('order_count'),
        func.sum(Order.price).label('total_revenue')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.id, Vehicle.make, Vehicle.model).order_by(
        desc('order_count')
    ).limit(5).all()
    
    # User growth (last 30 days)
    user_growth = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('new_users')
    ).filter(
        User.created_at >= thirty_days_ago
    ).group_by(func.date(User.created_at)).all()
    
    # Convert date objects to strings for template rendering
    daily_sales_formatted = []
    for sale in daily_sales:
        daily_sales_formatted.append({
            'date': sale.date.strftime('%Y-%m-%d') if hasattr(sale.date, 'strftime') else str(sale.date),
            'orders': sale.orders,
            'revenue': float(sale.revenue) if sale.revenue else 0
        })
    
    user_growth_formatted = []
    for growth in user_growth:
        user_growth_formatted.append({
            'date': growth.date.strftime('%Y-%m-%d') if hasattr(growth.date, 'strftime') else str(growth.date),
            'new_users': growth.new_users
        })
    
    # Order status distribution
    order_status_stats = db.session.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    
    # Negotiation status distribution
    negotiation_status_stats = db.session.query(
        Negotiation.status,
        func.count(Negotiation.id).label('count')
    ).group_by(Negotiation.status).all()
    
    # Monthly revenue comparison
    current_month = datetime.utcnow().replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    
    current_month_revenue = db.session.query(func.sum(Order.price)).filter(
        and_(
            Order.created_at >= current_month,
            Order.status == 'paid'
        )
    ).scalar() or 0
    
    last_month_revenue = db.session.query(func.sum(Order.price)).filter(
        and_(
            Order.created_at >= last_month,
            Order.created_at < current_month,
            Order.status == 'paid'
        )
    ).scalar() or 0
    
    # Calculate percentage change
    revenue_change = 0
    if last_month_revenue > 0:
        revenue_change = ((current_month_revenue - last_month_revenue) / last_month_revenue) * 100
    
    return render_template('admin/dashboard.html',
                         total_vehicles=total_vehicles,
                         total_users=total_users,
                         total_orders=total_orders,
                         total_negotiations=total_negotiations,
                         total_revenue=total_revenue,
                         recent_orders=recent_orders,
                         recent_negotiations=recent_negotiations,
                         recent_users=recent_users,
                         daily_sales=daily_sales_formatted,
                         popular_vehicles=popular_vehicles,
                         user_growth=user_growth_formatted,
                         order_status_stats=order_status_stats,
                         negotiation_status_stats=negotiation_status_stats,
                         current_month_revenue=current_month_revenue,
                         last_month_revenue=last_month_revenue,
                         revenue_change=revenue_change)

@admin_bp.route('/vehicles')
@login_required
@admin_required
def vehicles():
    """Admin vehicle management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    make_filter = request.args.get('make', '')
    year_filter = request.args.get('year', '')
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = Vehicle.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            or_(
                Vehicle.make.ilike(f'%{search_query}%'),
                Vehicle.model.ilike(f'%{search_query}%'),
                Vehicle.color.ilike(f'%{search_query}%')
            )
        )
    
    # Apply make filter
    if make_filter:
        query = query.filter(Vehicle.make.ilike(f'%{make_filter}%'))
    
    # Apply year filter
    if year_filter:
        query = query.filter(Vehicle.year == int(year_filter))
    
    # Apply price filters
    if price_min:
        query = query.filter(Vehicle.price >= price_min)
    if price_max:
        query = query.filter(Vehicle.price <= price_max)
    
    # Apply sorting
    if sort_by == 'price':
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.price))
        else:
            query = query.order_by(desc(Vehicle.price))
    elif sort_by == 'year':
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.year))
        else:
            query = query.order_by(desc(Vehicle.year))
    elif sort_by == 'mileage':
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.mileage))
        else:
            query = query.order_by(desc(Vehicle.mileage))
    elif sort_by == 'make':
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.make))
        else:
            query = query.order_by(desc(Vehicle.make))
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.created_at))
        else:
            query = query.order_by(desc(Vehicle.created_at))
    
    # Paginate results
    vehicles = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique makes and years for filters
    unique_makes = db.session.query(Vehicle.make).distinct().order_by(Vehicle.make).all()
    unique_years = db.session.query(Vehicle.year).distinct().order_by(desc(Vehicle.year)).all()
    
    return render_template('admin/vehicles/list.html',
                         vehicles=vehicles,
                         search_query=search_query,
                         make_filter=make_filter,
                         year_filter=year_filter,
                         price_min=price_min,
                         price_max=price_max,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         unique_makes=unique_makes,
                         unique_years=unique_years)

@admin_bp.route('/vehicles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_vehicle():
    """Create a new vehicle"""
    from app.forms import AdminVehicleForm
    
    form = AdminVehicleForm()
    
    if form.validate_on_submit():
        try:
            # Create new vehicle
            vehicle = Vehicle(
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
            
            db.session.add(vehicle)
            db.session.commit()
            
            flash(f'Vehicle "{vehicle.make} {vehicle.model}" created successfully!', 'success')
            return redirect(url_for('admin.vehicles'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the vehicle.', 'error')
    
    return render_template('admin/vehicles/create.html', form=form)

@admin_bp.route('/vehicles/<int:vehicle_id>')
@login_required
@admin_required
def view_vehicle(vehicle_id):
    """View vehicle details"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Get vehicle images
    images = VehicleImage.query.filter_by(vehicle_id=vehicle_id).all()
    
    # Get vehicle categories
    vehicle_categories = db.session.query(Category).join(VehicleCategory).filter(
        VehicleCategory.vehicle_id == vehicle_id
    ).all()
    
    # Get orders for this vehicle
    orders = Order.query.filter_by(vehicle_id=vehicle_id).order_by(desc(Order.created_at)).limit(10).all()
    
    # Get negotiations for this vehicle
    negotiations = Negotiation.query.filter_by(vehicle_id=vehicle_id).order_by(desc(Negotiation.created_at)).limit(10).all()
    
    return render_template('admin/vehicles/detail.html',
                         vehicle=vehicle,
                         images=images,
                         categories=vehicle_categories,
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
            # Update vehicle
            vehicle.make = form.make.data
            vehicle.model = form.model.data
            vehicle.year = form.year.data
            vehicle.mileage = form.mileage.data
            vehicle.engine_type = form.engine_type.data
            vehicle.transmission = form.transmission.data
            vehicle.body_type = form.body_type.data
            vehicle.color = form.color.data
            vehicle.price = form.price.data
            vehicle.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Vehicle "{vehicle.make} {vehicle.model}" updated successfully!', 'success')
            return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the vehicle.', 'error')
    
    return render_template('admin/vehicles/edit.html', form=form, vehicle=vehicle)

@admin_bp.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vehicle(vehicle_id):
    """Delete a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    try:
        # Check if vehicle has orders or negotiations
        has_orders = Order.query.filter_by(vehicle_id=vehicle_id).first() is not None
        has_negotiations = Negotiation.query.filter_by(vehicle_id=vehicle_id).first() is not None
        
        if has_orders or has_negotiations:
            flash('Cannot delete vehicle with existing orders or negotiations.', 'error')
            return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))
        
        # Delete vehicle images
        VehicleImage.query.filter_by(vehicle_id=vehicle_id).delete()
        
        # Delete vehicle categories
        VehicleCategory.query.filter_by(vehicle_id=vehicle_id).delete()
        
        # Delete discount rules
        DiscountRule.query.filter_by(vehicle_id=vehicle_id).delete()
        
        # Delete vehicle
        db.session.delete(vehicle)
        db.session.commit()
        
        flash(f'Vehicle "{vehicle.make} {vehicle.model}" deleted successfully!', 'success')
        return redirect(url_for('admin.vehicles'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the vehicle.', 'error')
        return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))

@admin_bp.route('/vehicles/<int:vehicle_id>/images', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_vehicle_images(vehicle_id):
    """Manage vehicle images"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'POST':
        try:
            # Handle image upload (simplified - in real app, you'd handle file uploads)
            image_url = request.form.get('image_url')
            is_primary = request.form.get('is_primary') == 'on'
            
            if image_url:
                # If setting as primary, unset other primary images
                if is_primary:
                    VehicleImage.query.filter_by(vehicle_id=vehicle_id, is_primary=True).update({'is_primary': False})
                
                # Create new image
                vehicle_image = VehicleImage(
                    vehicle_id=vehicle_id,
                    image_url=image_url,
                    is_primary=is_primary
                )
                
                db.session.add(vehicle_image)
                db.session.commit()
                
                flash('Image added successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while adding the image.', 'error')
    
    # Get all images for this vehicle
    images = VehicleImage.query.filter_by(vehicle_id=vehicle_id).order_by(VehicleImage.is_primary.desc(), VehicleImage.created_at).all()
    
    return render_template('admin/vehicles/images.html', vehicle=vehicle, images=images)

@admin_bp.route('/vehicles/<int:vehicle_id>/images/<int:image_id>/set-primary', methods=['POST'])
@login_required
@admin_required
def set_primary_image(vehicle_id, image_id):
    """Set an image as primary"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    image = VehicleImage.query.filter_by(id=image_id, vehicle_id=vehicle_id).first_or_404()
    
    try:
        # Unset all other primary images for this vehicle
        VehicleImage.query.filter_by(vehicle_id=vehicle_id, is_primary=True).update({'is_primary': False})
        
        # Set this image as primary
        image.is_primary = True
        db.session.commit()
        
        flash('Primary image updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the primary image.', 'error')
    
    return redirect(url_for('admin.manage_vehicle_images', vehicle_id=vehicle_id))

@admin_bp.route('/vehicles/<int:vehicle_id>/images/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vehicle_image(vehicle_id, image_id):
    """Delete a vehicle image"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    image = VehicleImage.query.filter_by(id=image_id, vehicle_id=vehicle_id).first_or_404()
    
    try:
        db.session.delete(image)
        db.session.commit()
        
        flash('Image deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the image.', 'error')
    
    return redirect(url_for('admin.manage_vehicle_images', vehicle_id=vehicle_id))

@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Manage vehicle categories"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories/list.html', categories=categories)

@admin_bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_category():
    """Create a new category"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Category name is required.', 'error')
                return render_template('admin/categories/create.html')
            
            # Check if category already exists
            existing_category = Category.query.filter_by(name=name).first()
            if existing_category:
                flash('A category with this name already exists.', 'error')
                return render_template('admin/categories/create.html')
            
            category = Category(name=name, description=description)
            db.session.add(category)
            db.session.commit()
            
            flash(f'Category "{category.name}" created successfully!', 'success')
            return redirect(url_for('admin.categories'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the category.', 'error')
    
    return render_template('admin/categories/create.html')

@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit a category"""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                flash('Category name is required.', 'error')
                return render_template('admin/categories/edit.html', category=category)
            
            # Check if another category with this name exists
            existing_category = Category.query.filter(Category.name == name, Category.id != category_id).first()
            if existing_category:
                flash('A category with this name already exists.', 'error')
                return render_template('admin/categories/edit.html', category=category)
            
            category.name = name
            category.description = description
            db.session.commit()
            
            flash(f'Category "{category.name}" updated successfully!', 'success')
            return redirect(url_for('admin.categories'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the category.', 'error')
    
    return render_template('admin/categories/edit.html', category=category)

@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete a category"""
    category = Category.query.get_or_404(category_id)
    
    try:
        # Check if category is used by any vehicles
        vehicle_count = VehicleCategory.query.filter_by(category_id=category_id).count()
        
        if vehicle_count > 0:
            flash(f'Cannot delete category "{category.name}" because it is used by {vehicle_count} vehicle(s).', 'error')
            return redirect(url_for('admin.categories'))
        
        db.session.delete(category)
        db.session.commit()
        
        flash(f'Category "{category.name}" deleted successfully!', 'success')
        return redirect(url_for('admin.categories'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the category.', 'error')
        return redirect(url_for('admin.categories'))

@admin_bp.route('/vehicles/<int:vehicle_id>/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_vehicle_categories(vehicle_id):
    """Manage vehicle categories"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    if request.method == 'POST':
        try:
            # Get selected category IDs
            selected_categories = request.form.getlist('categories')
            
            # Remove existing category assignments
            VehicleCategory.query.filter_by(vehicle_id=vehicle_id).delete()
            
            # Add new category assignments
            for category_id in selected_categories:
                if category_id:  # Skip empty values
                    vehicle_category = VehicleCategory(
                        vehicle_id=vehicle_id,
                        category_id=int(category_id)
                    )
                    db.session.add(vehicle_category)
            
            db.session.commit()
            
            flash('Vehicle categories updated successfully!', 'success')
            return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating vehicle categories.', 'error')
    
    # Get all categories
    all_categories = Category.query.order_by(Category.name).all()
    
    # Get current vehicle categories
    current_categories = db.session.query(Category).join(VehicleCategory).filter(
        VehicleCategory.vehicle_id == vehicle_id
    ).all()
    current_category_ids = [cat.id for cat in current_categories]
    
    return render_template('admin/vehicles/categories.html', 
                         vehicle=vehicle, 
                         all_categories=all_categories,
                         current_category_ids=current_category_ids)

@admin_bp.route('/vehicles/bulk-actions', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_vehicle_actions():
    """Handle bulk operations on vehicles"""
    if request.method == 'POST':
        action = request.form.get('action')
        vehicle_ids = request.form.getlist('vehicle_ids')
        
        if not vehicle_ids:
            flash('No vehicles selected.', 'error')
            return redirect(url_for('admin.vehicles'))
        
        try:
            if action == 'delete':
                # Check if any vehicles have orders or negotiations
                vehicles_with_orders = db.session.query(Vehicle.id).join(Order).filter(
                    Vehicle.id.in_(vehicle_ids)
                ).distinct().all()
                
                vehicles_with_negotiations = db.session.query(Vehicle.id).join(Negotiation).filter(
                    Vehicle.id.in_(vehicle_ids)
                ).distinct().all()
                
                if vehicles_with_orders or vehicles_with_negotiations:
                    flash('Cannot delete vehicles with existing orders or negotiations.', 'error')
                    return redirect(url_for('admin.vehicles'))
                
                # Delete vehicle images, categories, and discount rules
                for vehicle_id in vehicle_ids:
                    VehicleImage.query.filter_by(vehicle_id=vehicle_id).delete()
                    VehicleCategory.query.filter_by(vehicle_id=vehicle_id).delete()
                    DiscountRule.query.filter_by(vehicle_id=vehicle_id).delete()
                
                # Delete vehicles
                Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).delete(synchronize_session=False)
                db.session.commit()
                
                flash(f'{len(vehicle_ids)} vehicles deleted successfully!', 'success')
                
            elif action == 'export':
                # Export selected vehicles to CSV
                vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all()
                return export_vehicles_csv(vehicles)
                
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while performing the bulk action.', 'error')
    
    return redirect(url_for('admin.vehicles'))

@admin_bp.route('/vehicles/export')
@login_required
@admin_required
def export_all_vehicles():
    """Export all vehicles to CSV"""
    vehicles = Vehicle.query.all()
    return export_vehicles_csv(vehicles)

@admin_bp.route('/vehicles/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_vehicles():
    """Import vehicles from CSV"""
    if request.method == 'POST':
        try:
            # In a real application, you would handle file upload here
            # For now, we'll just show a placeholder
            flash('Vehicle import functionality would be implemented here.', 'info')
            return redirect(url_for('admin.vehicles'))
            
        except Exception as e:
            flash('An error occurred while importing vehicles.', 'error')
    
    return render_template('admin/vehicles/import.html')

def export_vehicles_csv(vehicles):
    """Helper function to export vehicles to CSV"""
    import csv
    import io
    from flask import make_response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Make', 'Model', 'Year', 'Mileage', 'Engine Type', 
        'Transmission', 'Body Type', 'Color', 'Price', 'Created At'
    ])
    
    # Write data
    for vehicle in vehicles:
        writer.writerow([
            vehicle.id,
            vehicle.make,
            vehicle.model,
            vehicle.year,
            vehicle.mileage,
            vehicle.engine_type,
            vehicle.transmission,
            vehicle.body_type,
            vehicle.color,
            vehicle.price,
            vehicle.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=vehicles_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@admin_bp.route('/vehicles/<int:vehicle_id>/status', methods=['POST'])
@login_required
@admin_required
def update_vehicle_status(vehicle_id):
    """Update vehicle availability status"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    try:
        status = request.form.get('status')
        
        if status not in ['available', 'sold', 'reserved', 'maintenance']:
            flash('Invalid status provided.', 'error')
            return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))
        
        # In a real application, you would add a status field to the Vehicle model
        # For now, we'll use a simple approach with orders to determine status
        if status == 'sold':
            # Check if vehicle has a completed order
            completed_order = Order.query.filter_by(vehicle_id=vehicle_id, status='paid').first()
            if not completed_order:
                flash('Cannot mark as sold without a completed order.', 'error')
                return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))
        
        # Update vehicle status (this would be a field in the Vehicle model)
        # vehicle.status = status
        # vehicle.updated_at = datetime.utcnow()
        # db.session.commit()
        
        flash(f'Vehicle status updated to {status.title()}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating vehicle status.', 'error')
    
    return redirect(url_for('admin.view_vehicle', vehicle_id=vehicle_id))

@admin_bp.route('/inventory')
@login_required
@admin_required
def inventory():
    """Inventory tracking and management"""
    # Get inventory statistics
    total_vehicles = Vehicle.query.count()
    
    # Count vehicles by status (simplified - in real app, you'd have a status field)
    available_vehicles = Vehicle.query.filter(
        ~Vehicle.id.in_(
            db.session.query(Order.vehicle_id).filter(Order.status == 'paid')
        )
    ).count()
    
    sold_vehicles = Vehicle.query.filter(
        Vehicle.id.in_(
            db.session.query(Order.vehicle_id).filter(Order.status == 'paid')
        )
    ).count()
    
    # Get vehicles with pending orders (reserved)
    reserved_vehicles = Vehicle.query.filter(
        Vehicle.id.in_(
            db.session.query(Order.vehicle_id).filter(Order.status == 'pending')
        )
    ).count()
    
    # Get low stock alerts (vehicles with high demand)
    popular_vehicles = db.session.query(
        Vehicle.make, Vehicle.model, func.count(Order.id).label('order_count')
    ).join(Order, Vehicle.id == Order.vehicle_id).group_by(
        Vehicle.id, Vehicle.make, Vehicle.model
    ).order_by(desc('order_count')).limit(5).all()
    
    # Get recent inventory changes
    recent_orders = Order.query.order_by(desc(Order.created_at)).limit(10).all()
    
    # Get vehicles by category
    vehicles_by_category = db.session.query(
        Category.name, func.count(Vehicle.id).label('count')
    ).join(VehicleCategory).join(Vehicle).group_by(Category.name).all()
    
    return render_template('admin/inventory/dashboard.html',
                         total_vehicles=total_vehicles,
                         available_vehicles=available_vehicles,
                         sold_vehicles=sold_vehicles,
                         reserved_vehicles=reserved_vehicles,
                         popular_vehicles=popular_vehicles,
                         recent_orders=recent_orders,
                         vehicles_by_category=vehicles_by_category)

@admin_bp.route('/inventory/reports')
@login_required
@admin_required
def inventory_reports():
    """Generate inventory reports"""
    # Sales trends by month
    monthly_sales = db.session.query(
        func.date_trunc('month', Order.created_at).label('month'),
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue')
    ).filter(Order.status == 'paid').group_by(
        func.date_trunc('month', Order.created_at)
    ).order_by('month').all()
    
    # Top performing vehicles
    top_vehicles = db.session.query(
        Vehicle.make, Vehicle.model, func.count(Order.id).label('sales'),
        func.sum(Order.price).label('revenue')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.id, Vehicle.make, Vehicle.model).order_by(
        desc('sales')
    ).limit(10).all()
    
    # Inventory turnover
    turnover_data = db.session.query(
        Vehicle.make, Vehicle.model,
        func.count(Order.id).label('total_orders'),
        func.avg(func.extract('day', Order.created_at - Vehicle.created_at)).label('avg_days_to_sell')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.id, Vehicle.make, Vehicle.model).all()
    
    return render_template('admin/inventory/reports.html',
                         monthly_sales=monthly_sales,
                         top_vehicles=top_vehicles,
                         turnover_data=turnover_data)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Admin user management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = User.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            or_(
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )
    
    # Apply role filter
    if role_filter:
        query = query.filter(User.role == int(role_filter))
    
    # Apply status filter (assuming we have an is_active field)
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'asc':
            query = query.order_by(asc(User.name))
        else:
            query = query.order_by(desc(User.name))
    elif sort_by == 'email':
        if sort_order == 'asc':
            query = query.order_by(asc(User.email))
        else:
            query = query.order_by(desc(User.email))
    elif sort_by == 'role':
        if sort_order == 'asc':
            query = query.order_by(asc(User.role))
        else:
            query = query.order_by(desc(User.role))
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(User.created_at))
        else:
            query = query.order_by(desc(User.created_at))
    
    # Paginate results
    users = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get user statistics
    total_users = User.query.count()
    admin_users = User.query.filter(User.role == 1).count()
    regular_users = User.query.filter(User.role == 2).count()
    active_users = User.query.filter(User.is_active == True).count()
    
    return render_template('admin/users/list.html',
                         users=users,
                         search_query=search_query,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_users=total_users,
                         admin_users=admin_users,
                         regular_users=regular_users,
                         active_users=active_users)

@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View user details"""
    user = User.query.get_or_404(user_id)
    
    # Get user orders
    orders = Order.query.filter_by(user_id=user_id).order_by(desc(Order.created_at)).all()
    
    # Get user negotiations
    negotiations = Negotiation.query.filter_by(user_id=user_id).order_by(desc(Negotiation.created_at)).all()
    
    # Get user reviews
    reviews = Review.query.filter_by(user_id=user_id).order_by(desc(Review.created_at)).all()
    
    # Calculate user statistics
    total_orders = len(orders)
    total_spent = sum(order.price for order in orders if order.status == 'paid')
    total_negotiations = len(negotiations)
    successful_negotiations = len([n for n in negotiations if n.status == 'accepted'])
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_orders = Order.query.filter(
        Order.user_id == user_id,
        Order.created_at >= thirty_days_ago
    ).count()
    
    recent_negotiations = Negotiation.query.filter(
        Negotiation.user_id == user_id,
        Negotiation.created_at >= thirty_days_ago
    ).count()
    
    return render_template('admin/users/detail.html',
                         user=user,
                         orders=orders,
                         negotiations=negotiations,
                         reviews=reviews,
                         total_orders=total_orders,
                         total_spent=total_spent,
                         total_negotiations=total_negotiations,
                         successful_negotiations=successful_negotiations,
                         recent_orders=recent_orders,
                         recent_negotiations=recent_negotiations)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update user information
            user.name = request.form.get('name', user.name)
            user.email = request.form.get('email', user.email)
            user.role = int(request.form.get('role', user.role))
            user.is_active = request.form.get('is_active') == 'on'
            
            # Update password if provided
            new_password = request.form.get('new_password')
            if new_password:
                from passlib.hash import sha256_crypt
                user.password = sha256_crypt.encrypt(new_password)
            
            db.session.commit()
            
            flash(f'User "{user.name}" updated successfully!', 'success')
            return redirect(url_for('admin.view_user', user_id=user_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating the user.', 'error')
    
    return render_template('admin/users/edit.html', user=user)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User "{user.name}" has been {status}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating user status.', 'error')
    
    return redirect(url_for('admin.view_user', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))
    
    try:
        # Check if user has orders or negotiations
        has_orders = Order.query.filter_by(user_id=user_id).first() is not None
        has_negotiations = Negotiation.query.filter_by(user_id=user_id).first() is not None
        
        if has_orders or has_negotiations:
            flash('Cannot delete user with existing orders or negotiations. Consider deactivating instead.', 'error')
            return redirect(url_for('admin.view_user', user_id=user_id))
        
        # Delete user reviews
        Review.query.filter_by(user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{user.name}" deleted successfully!', 'success')
        return redirect(url_for('admin.users'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the user.', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

@admin_bp.route('/users/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_user_actions():
    """Handle bulk operations on users"""
    action = request.form.get('action')
    user_ids = request.form.getlist('user_ids')
    
    if not user_ids:
        flash('No users selected.', 'error')
        return redirect(url_for('admin.users'))
    
    # Remove current user from selection to prevent self-modification
    user_ids = [uid for uid in user_ids if int(uid) != current_user.id]
    
    if not user_ids:
        flash('No valid users selected for bulk action.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        if action == 'activate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': True}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(user_ids)} users activated successfully!', 'success')
            
        elif action == 'deactivate':
            User.query.filter(User.id.in_(user_ids)).update({'is_active': False}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(user_ids)} users deactivated successfully!', 'success')
            
        elif action == 'make_admin':
            User.query.filter(User.id.in_(user_ids)).update({'role': 1}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(user_ids)} users promoted to admin!', 'success')
            
        elif action == 'make_user':
            User.query.filter(User.id.in_(user_ids)).update({'role': 2}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(user_ids)} users demoted to regular user!', 'success')
            
        elif action == 'delete':
            # Check for users with orders/negotiations
            users_with_data = db.session.query(User.id).filter(
                or_(
                    User.id.in_(db.session.query(Order.user_id)),
                    User.id.in_(db.session.query(Negotiation.user_id))
                ),
                User.id.in_(user_ids)
            ).all()
            
            if users_with_data:
                flash(f'Cannot delete {len(users_with_data)} users with existing orders or negotiations.', 'error')
                return redirect(url_for('admin.users'))
            
            # Delete user reviews first
            Review.query.filter(Review.user_id.in_(user_ids)).delete(synchronize_session=False)
            
            # Delete users
            User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
            db.session.commit()
            
            flash(f'{len(user_ids)} users deleted successfully!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while performing the bulk action.', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/pending-approval')
@login_required
@admin_required
def pending_user_approvals():
    """View users pending approval"""
    # In a real application, you would have a field like 'is_approved' or 'status'
    # For now, we'll show inactive users as pending approval
    pending_users = User.query.filter(User.is_active == False).order_by(desc(User.created_at)).all()
    
    return render_template('admin/users/pending_approval.html', pending_users=pending_users)

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    """Approve a user registration"""
    user = User.query.get_or_404(user_id)
    
    try:
        user.is_active = True
        db.session.commit()
        
        flash(f'User "{user.name}" has been approved and can now access the system.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while approving the user.', 'error')
    
    return redirect(url_for('admin.pending_user_approvals'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    """Reject a user registration"""
    user = User.query.get_or_404(user_id)
    
    try:
        # In a real application, you might want to keep the user record but mark as rejected
        # For now, we'll delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User registration for "{user.name}" has been rejected.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while rejecting the user.', 'error')
    
    return redirect(url_for('admin.pending_user_approvals'))

@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """Admin order management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    payment_filter = request.args.get('payment', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = Order.query
    
    # Apply search filter
    if search_query:
        query = query.join(User).join(Vehicle).filter(
            or_(
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%'),
                Vehicle.make.ilike(f'%{search_query}%'),
                Vehicle.model.ilike(f'%{search_query}%')
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    # Apply payment filter
    if payment_filter:
        if payment_filter == 'paid':
            query = query.filter(Order.status == 'paid')
        elif payment_filter == 'pending':
            query = query.filter(Order.status == 'pending')
        elif payment_filter == 'failed':
            query = query.filter(Order.status == 'failed')
    
    # Apply date filters
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
        if sort_order == 'asc':
            query = query.order_by(asc(Order.price))
        else:
            query = query.order_by(desc(Order.price))
    elif sort_by == 'customer':
        if sort_order == 'asc':
            query = query.join(User).order_by(asc(User.name))
        else:
            query = query.join(User).order_by(desc(User.name))
    elif sort_by == 'vehicle':
        if sort_order == 'asc':
            query = query.join(Vehicle).order_by(asc(Vehicle.make))
        else:
            query = query.join(Vehicle).order_by(desc(Vehicle.make))
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(Order.created_at))
        else:
            query = query.order_by(desc(Order.created_at))
    
    # Paginate results
    orders = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get order statistics
    total_orders = Order.query.count()
    paid_orders = Order.query.filter(Order.status == 'paid').count()
    pending_orders = Order.query.filter(Order.status == 'pending').count()
    failed_orders = Order.query.filter(Order.status == 'failed').count()
    
    # Calculate total revenue
    total_revenue = db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0
    
    return render_template('admin/orders/list.html',
                         orders=orders,
                         search_query=search_query,
                         status_filter=status_filter,
                         payment_filter=payment_filter,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_orders=total_orders,
                         paid_orders=paid_orders,
                         pending_orders=pending_orders,
                         failed_orders=failed_orders,
                         total_revenue=total_revenue)

@admin_bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def view_order(order_id):
    """View order details"""
    order = Order.query.get_or_404(order_id)
    
    # Get payment information if available
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    # Get order history/status changes (if you have an OrderStatusHistory model)
    # For now, we'll just show the current status
    
    return render_template('admin/orders/detail.html',
                         order=order,
                         payment=payment)

@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    """Update order status"""
    order = Order.query.get_or_404(order_id)
    
    try:
        new_status = request.form.get('status')
        
        if new_status not in ['pending', 'paid', 'shipped', 'delivered', 'cancelled', 'failed']:
            flash('Invalid status provided.', 'error')
            return redirect(url_for('admin.view_order', order_id=order_id))
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # If marking as paid, update payment record
        if new_status == 'paid' and old_status != 'paid':
            payment = Payment.query.filter_by(order_id=order_id).first()
            if payment:
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()
            else:
                # Create payment record
                payment = Payment(
                    order_id=order_id,
                    amount=order.price,
                    status='completed',
                    payment_method='admin_override',
                    completed_at=datetime.utcnow()
                )
                db.session.add(payment)
        
        db.session.commit()
        
        flash(f'Order status updated from {old_status.title()} to {new_status.title()}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the order status.', 'error')
    
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_order(order_id):
    """Cancel an order"""
    order = Order.query.get_or_404(order_id)
    
    try:
        if order.status in ['delivered', 'cancelled']:
            flash('Cannot cancel an order that has been delivered or is already cancelled.', 'error')
            return redirect(url_for('admin.view_order', order_id=order_id))
        
        order.status = 'cancelled'
        order.updated_at = datetime.utcnow()
        
        # Update payment status if exists
        payment = Payment.query.filter_by(order_id=order_id).first()
        if payment:
            payment.status = 'cancelled'
        
        db.session.commit()
        
        flash('Order has been cancelled successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the order.', 'error')
    
    return redirect(url_for('admin.view_order', order_id=order_id))

@admin_bp.route('/orders/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_order_actions():
    """Handle bulk operations on orders"""
    action = request.form.get('action')
    order_ids = request.form.getlist('order_ids')
    
    if not order_ids:
        flash('No orders selected.', 'error')
        return redirect(url_for('admin.orders'))
    
    try:
        if action == 'mark_paid':
            Order.query.filter(Order.id.in_(order_ids)).update({'status': 'paid'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(order_ids)} orders marked as paid!', 'success')
            
        elif action == 'mark_shipped':
            Order.query.filter(Order.id.in_(order_ids)).update({'status': 'shipped'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(order_ids)} orders marked as shipped!', 'success')
            
        elif action == 'mark_delivered':
            Order.query.filter(Order.id.in_(order_ids)).update({'status': 'delivered'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(order_ids)} orders marked as delivered!', 'success')
            
        elif action == 'cancel':
            Order.query.filter(Order.id.in_(order_ids)).update({'status': 'cancelled'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(order_ids)} orders cancelled!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while performing the bulk action.', 'error')
    
    return redirect(url_for('admin.orders'))

@admin_bp.route('/orders/analytics')
@login_required
@admin_required
def order_analytics():
    """Order analytics and reports"""
    # Revenue by month (last 12 months) - SQLite compatible
    monthly_revenue = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue')
    ).filter(Order.status == 'paid').group_by(
        func.strftime('%Y-%m', Order.created_at)
    ).order_by('month').limit(12).all()
    
    # Top selling vehicles
    top_vehicles = db.session.query(
        Vehicle.make, Vehicle.model, func.count(Order.id).label('sales'),
        func.sum(Order.price).label('revenue')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.id, Vehicle.make, Vehicle.model).order_by(
        desc('sales')
    ).limit(10).all()
    
    # Order status distribution
    status_distribution = db.session.query(
        Order.status, func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    
    # Revenue by customer (top customers)
    top_customers = db.session.query(
        User.name, User.email, func.count(Order.id).label('orders'),
        func.sum(Order.price).label('total_spent')
    ).join(Order, User.id == Order.user_id).filter(
        Order.status == 'paid'
    ).group_by(User.id, User.name, User.email).order_by(
        desc('total_spent')
    ).limit(10).all()
    
    # Daily sales (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue')
    ).filter(
        Order.status == 'paid',
        Order.created_at >= thirty_days_ago
    ).group_by(func.date(Order.created_at)).order_by('date').all()
    
    return render_template('admin/orders/analytics.html',
                         monthly_revenue=monthly_revenue,
                         top_vehicles=top_vehicles,
                         status_distribution=status_distribution,
                         top_customers=top_customers,
                         daily_sales=daily_sales)

@admin_bp.route('/negotiations')
@login_required
@admin_required
def negotiations():
    """Admin negotiation management page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = Negotiation.query
    
    # Apply search filter
    if search_query:
        query = query.join(User).join(Vehicle).filter(
            or_(
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%'),
                Vehicle.make.ilike(f'%{search_query}%'),
                Vehicle.model.ilike(f'%{search_query}%')
            )
        )
    
    # Apply status filter
    if status_filter:
        query = query.filter(Negotiation.status == status_filter)
    
    # Apply date filters
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
        if sort_order == 'asc':
            query = query.order_by(asc(Negotiation.final_price))
        else:
            query = query.order_by(desc(Negotiation.final_price))
    elif sort_by == 'customer':
        if sort_order == 'asc':
            query = query.join(User).order_by(asc(User.name))
        else:
            query = query.join(User).order_by(desc(User.name))
    elif sort_by == 'vehicle':
        if sort_order == 'asc':
            query = query.join(Vehicle).order_by(asc(Vehicle.make))
        else:
            query = query.join(Vehicle).order_by(desc(Vehicle.make))
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(Negotiation.created_at))
        else:
            query = query.order_by(desc(Negotiation.created_at))
    
    # Paginate results
    negotiations = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get negotiation statistics
    total_negotiations = Negotiation.query.count()
    ongoing_negotiations = Negotiation.query.filter(Negotiation.status == 'ongoing').count()
    accepted_negotiations = Negotiation.query.filter(Negotiation.status == 'accepted').count()
    rejected_negotiations = Negotiation.query.filter(Negotiation.status == 'rejected').count()
    
    # Calculate average negotiation value
    avg_negotiation_value = db.session.query(func.avg(Negotiation.final_price)).filter(
        Negotiation.final_price.isnot(None)
    ).scalar() or 0
    
    return render_template('admin/negotiations/list.html',
                         negotiations=negotiations,
                         search_query=search_query,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_negotiations=total_negotiations,
                         ongoing_negotiations=ongoing_negotiations,
                         accepted_negotiations=accepted_negotiations,
                         rejected_negotiations=rejected_negotiations,
                         avg_negotiation_value=avg_negotiation_value)

@admin_bp.route('/negotiations/<int:negotiation_id>')
@login_required
@admin_required
def view_negotiation(negotiation_id):
    """View negotiation details"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Get all offers for this negotiation
    offers = NegotiationOffer.query.filter_by(negotiation_id=negotiation_id).order_by(NegotiationOffer.created_at).all()
    
    # Get negotiation statistics
    total_offers = len(offers)
    user_offers = [offer for offer in offers if offer.offer_type == 'user']
    admin_offers = [offer for offer in offers if offer.offer_type == 'admin']
    
    return render_template('admin/negotiations/detail.html',
                         negotiation=negotiation,
                         offers=offers,
                         total_offers=total_offers,
                         user_offers=user_offers,
                         admin_offers=admin_offers)

@admin_bp.route('/negotiations/<int:negotiation_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_negotiation_status(negotiation_id):
    """Update negotiation status"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    try:
        new_status = request.form.get('status')
        
        if new_status not in ['ongoing', 'accepted', 'rejected', 'cancelled']:
            flash('Invalid status provided.', 'error')
            return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))
        
        old_status = negotiation.status
        negotiation.status = new_status
        negotiation.updated_at = datetime.utcnow()
        
        # If accepting, set final price to the latest offer
        if new_status == 'accepted' and old_status != 'accepted':
            latest_offer = NegotiationOffer.query.filter_by(
                negotiation_id=negotiation_id
            ).order_by(desc(NegotiationOffer.created_at)).first()
            
            if latest_offer:
                negotiation.final_price = latest_offer.offer_price
        
        db.session.commit()
        
        flash(f'Negotiation status updated from {old_status.title()} to {new_status.title()}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating the negotiation status.', 'error')
    
    return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/make-offer', methods=['POST'])
@login_required
@admin_required
def make_negotiation_offer(negotiation_id):
    """Make a counter-offer as admin"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    try:
        amount = float(request.form.get('amount'))
        message = request.form.get('message', '')
        
        if amount <= 0:
            flash('Offer amount must be greater than 0.', 'error')
            return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))
        
        # Create admin offer
        from app.models import OfferByEnum
        offer = NegotiationOffer(
            negotiation_id=negotiation_id,
            offer_by=OfferByEnum.AI,
            offer_price=amount,
            reason=message
        )
        
        db.session.add(offer)
        
        # Update negotiation
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Counter-offer of ${amount:,.2f} has been made.', 'success')
        
    except ValueError:
        flash('Invalid amount provided.', 'error')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while making the offer.', 'error')
    
    return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/accept-offer/<int:offer_id>', methods=['POST'])
@login_required
@admin_required
def accept_negotiation_offer(negotiation_id, offer_id):
    """Accept a specific offer"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    offer = NegotiationOffer.query.get_or_404(offer_id)
    
    try:
        # Update negotiation
        negotiation.status = 'accepted'
        negotiation.final_price = offer.offer_price
        negotiation.updated_at = datetime.utcnow()
        
        # Note: NegotiationOffer model doesn't have a status field
        # The negotiation status is what matters for tracking acceptance
        
        db.session.commit()
        
        flash(f'Offer of ${offer.offer_price:,.2f} has been accepted.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while accepting the offer.', 'error')
    
    return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/<int:negotiation_id>/reject-offer/<int:offer_id>', methods=['POST'])
@login_required
@admin_required
def reject_negotiation_offer(negotiation_id, offer_id):
    """Reject a specific offer"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    offer = NegotiationOffer.query.get_or_404(offer_id)
    
    try:
        # Note: NegotiationOffer model doesn't have a status field
        # The negotiation status is what matters for tracking rejection
        
        # Update negotiation
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Offer of ${offer.offer_price:,.2f} has been rejected.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while rejecting the offer.', 'error')
    
    return redirect(url_for('admin.view_negotiation', negotiation_id=negotiation_id))

@admin_bp.route('/negotiations/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_negotiation_actions():
    """Handle bulk operations on negotiations"""
    action = request.form.get('action')
    negotiation_ids = request.form.getlist('negotiation_ids')
    
    if not negotiation_ids:
        flash('No negotiations selected.', 'error')
        return redirect(url_for('admin.negotiations'))
    
    try:
        if action == 'accept':
            Negotiation.query.filter(Negotiation.id.in_(negotiation_ids)).update({'status': 'accepted'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(negotiation_ids)} negotiations accepted!', 'success')
            
        elif action == 'reject':
            Negotiation.query.filter(Negotiation.id.in_(negotiation_ids)).update({'status': 'rejected'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(negotiation_ids)} negotiations rejected!', 'success')
            
        elif action == 'cancel':
            Negotiation.query.filter(Negotiation.id.in_(negotiation_ids)).update({'status': 'cancelled'}, synchronize_session=False)
            db.session.commit()
            flash(f'{len(negotiation_ids)} negotiations cancelled!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while performing the bulk action.', 'error')
    
    return redirect(url_for('admin.negotiations'))

@admin_bp.route('/negotiations/analytics')
@login_required
@admin_required
def negotiation_analytics():
    """Negotiation analytics and reports"""
    # Success rate by month (last 12 months)
    monthly_success = db.session.query(
        func.strftime('%Y-%m', Negotiation.created_at).label('month'),
        func.count(Negotiation.id).label('total'),
        func.sum(case((Negotiation.status == 'accepted', 1), else_=0)).label('accepted')
    ).group_by(
        func.strftime('%Y-%m', Negotiation.created_at)
    ).order_by('month').limit(12).all()
    
    # Average offer amounts by status
    avg_offers = db.session.query(
        Negotiation.status,
        func.avg(NegotiationOffer.offer_price).label('avg_amount'),
        func.count(NegotiationOffer.id).label('offer_count')
    ).join(NegotiationOffer, Negotiation.id == NegotiationOffer.negotiation_id).group_by(
        Negotiation.status
    ).all()
    
    # Top negotiating customers
    top_negotiators = db.session.query(
        User.name, User.email, func.count(Negotiation.id).label('negotiations'),
        func.sum(case((Negotiation.status == 'accepted', 1), else_=0)).label('successful'),
        func.avg(Negotiation.final_price).label('avg_final_price')
    ).join(Negotiation, User.id == Negotiation.user_id).group_by(
        User.id, User.name, User.email
    ).order_by(desc('negotiations')).limit(10).all()
    
    # Negotiation duration analysis
    duration_analysis = db.session.query(
        case(
            (func.julianday(Negotiation.updated_at) - func.julianday(Negotiation.created_at) <= 1, 'Same Day'),
            (func.julianday(Negotiation.updated_at) - func.julianday(Negotiation.created_at) <= 7, '1 Week'),
            (func.julianday(Negotiation.updated_at) - func.julianday(Negotiation.created_at) <= 30, '1 Month'),
            else_='More than 1 Month'
        ).label('duration'),
        func.count(Negotiation.id).label('count')
    ).filter(Negotiation.status.in_(['accepted', 'rejected'])).group_by('duration').all()
    
    # Daily negotiation activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_activity = db.session.query(
        func.date(Negotiation.created_at).label('date'),
        func.count(Negotiation.id).label('negotiations'),
        func.sum(case((Negotiation.status == 'accepted', 1), else_=0)).label('accepted')
    ).filter(
        Negotiation.created_at >= thirty_days_ago
    ).group_by(func.date(Negotiation.created_at)).order_by('date').all()
    
    return render_template('admin/negotiations/analytics.html',
                         monthly_success=monthly_success,
                         avg_offers=avg_offers,
                         top_negotiators=top_negotiators,
                         duration_analysis=duration_analysis,
                         daily_activity=daily_activity)


# ============================================================================
# REPORTS & ANALYTICS
# ============================================================================

@admin_bp.route('/reports')
@login_required
@admin_required
def reports_dashboard():
    """Main reports dashboard"""
    # Get summary statistics for the dashboard
    total_revenue = db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0
    total_orders = db.session.query(func.count(Order.id)).filter(Order.status == 'paid').scalar() or 0
    total_users = User.query.count()
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    return render_template('admin/reports/dashboard.html',
                         total_revenue=total_revenue,
                         total_orders=total_orders,
                         total_users=total_users,
                         avg_order_value=avg_order_value)


@admin_bp.route('/reports/sales')
@login_required
@admin_required
def sales_reports():
    """Sales reports - daily, weekly, monthly revenue"""
    # Get date range from request
    period = request.args.get('period', 'monthly')  # daily, weekly, monthly
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Set default date range if not provided
    if not start_date or not end_date:
        if period == 'daily':
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=30)
        elif period == 'weekly':
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(weeks=12)
        else:  # monthly
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=365)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Sales data based on period
    if period == 'daily':
        sales_data = db.session.query(
            func.date(Order.created_at).label('date'),
            func.count(Order.id).label('orders'),
            func.sum(Order.price).label('revenue'),
            func.avg(Order.price).label('avg_order_value')
        ).filter(
            Order.status == 'paid',
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        ).group_by(func.date(Order.created_at)).order_by('date').all()
        
    elif period == 'weekly':
        sales_data = db.session.query(
            func.strftime('%Y-W%W', Order.created_at).label('week'),
            func.count(Order.id).label('orders'),
            func.sum(Order.price).label('revenue'),
            func.avg(Order.price).label('avg_order_value')
        ).filter(
            Order.status == 'paid',
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        ).group_by(func.strftime('%Y-W%W', Order.created_at)).order_by('week').all()
        
    else:  # monthly
        sales_data = db.session.query(
            func.strftime('%Y-%m', Order.created_at).label('month'),
            func.count(Order.id).label('orders'),
            func.sum(Order.price).label('revenue'),
            func.avg(Order.price).label('avg_order_value')
        ).filter(
            Order.status == 'paid',
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        ).group_by(func.strftime('%Y-%m', Order.created_at)).order_by('month').all()
    
    # Summary statistics
    total_revenue = db.session.query(func.sum(Order.price)).filter(
        Order.status == 'paid',
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date
    ).scalar() or 0
    
    total_orders = db.session.query(func.count(Order.id)).filter(
        Order.status == 'paid',
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date
    ).scalar() or 0
    
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    return render_template('admin/reports/sales.html',
                         sales_data=sales_data,
                         period=period,
                         start_date=start_date,
                         end_date=end_date,
                         total_revenue=total_revenue,
                         total_orders=total_orders,
                         avg_order_value=avg_order_value)


@admin_bp.route('/reports/vehicles')
@login_required
@admin_required
def vehicle_performance():
    """Vehicle performance analytics - most/least popular vehicles"""
    # Most popular vehicles (by orders)
    popular_vehicles = db.session.query(
        Vehicle.id, Vehicle.make, Vehicle.model, Vehicle.year,
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue'),
        func.avg(Order.price).label('avg_price')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Vehicle.id, Vehicle.make, Vehicle.model, Vehicle.year).order_by(
        desc('orders')
    ).limit(20).all()
    
    # Least popular vehicles (no orders or few orders)
    least_popular = db.session.query(
        Vehicle.id, Vehicle.make, Vehicle.model, Vehicle.year,
        func.count(Order.id).label('orders'),
        Vehicle.price
    ).outerjoin(Order, and_(Vehicle.id == Order.vehicle_id, Order.status == 'paid')).group_by(
        Vehicle.id, Vehicle.make, Vehicle.model, Vehicle.year, Vehicle.price
    ).having(func.count(Order.id) <= 2).order_by('orders').limit(20).all()
    
    # Vehicle performance by category
    category_performance = db.session.query(
        Category.name,
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue'),
        func.avg(Order.price).label('avg_price')
    ).join(VehicleCategory, Category.id == VehicleCategory.category_id).join(
        Vehicle, VehicleCategory.vehicle_id == Vehicle.id
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(Category.name).order_by(desc('revenue')).all()
    
    # Vehicle age analysis
    age_analysis = db.session.query(
        case(
            (Vehicle.year >= 2020, '2020+'),
            (Vehicle.year >= 2015, '2015-2019'),
            (Vehicle.year >= 2010, '2010-2014'),
            else_='Pre-2010'
        ).label('age_group'),
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('revenue'),
        func.avg(Order.price).label('avg_price')
    ).join(Order, Vehicle.id == Order.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by('age_group').order_by(desc('revenue')).all()
    
    return render_template('admin/reports/vehicles.html',
                         popular_vehicles=popular_vehicles,
                         least_popular=least_popular,
                         category_performance=category_performance,
                         age_analysis=age_analysis)


@admin_bp.route('/reports/users')
@login_required
@admin_required
def user_analytics():
    """User analytics - registration trends, user behavior"""
    # Registration trends (monthly)
    registration_trends = db.session.query(
        func.strftime('%Y-%m', User.created_at).label('month'),
        func.count(User.id).label('registrations'),
        func.sum(case((User.role == 1, 1), else_=0)).label('admins'),
        func.sum(case((User.role == 2, 1), else_=0)).label('users')
    ).group_by(func.strftime('%Y-%m', User.created_at)).order_by('month').limit(12).all()
    
    # User activity analysis
    user_activity = db.session.query(
        case(
            (func.count(Order.id) == 0, 'No Orders'),
            (func.count(Order.id) <= 2, '1-2 Orders'),
            (func.count(Order.id) <= 5, '3-5 Orders'),
            (func.count(Order.id) <= 10, '6-10 Orders'),
            else_='10+ Orders'
        ).label('activity_level'),
        func.count(User.id).label('user_count'),
        func.sum(func.count(Order.id)).label('total_orders'),
        func.sum(func.sum(Order.price)).label('total_revenue')
    ).outerjoin(Order, User.id == Order.user_id).group_by(
        User.id, 'activity_level'
    ).group_by('activity_level').all()
    
    # Top customers by spending
    top_customers = db.session.query(
        User.name, User.email,
        func.count(Order.id).label('orders'),
        func.sum(Order.price).label('total_spent'),
        func.avg(Order.price).label('avg_order_value'),
        User.created_at
    ).join(Order, User.id == Order.user_id).filter(
        Order.status == 'paid'
    ).group_by(User.id, User.name, User.email, User.created_at).order_by(
        desc('total_spent')
    ).limit(20).all()
    
    # User engagement metrics
    engagement_metrics = {
        'total_users': User.query.count(),
        'active_users': User.query.filter(User.is_active == True).count(),
        'users_with_orders': db.session.query(User.id).join(Order).distinct().count(),
        'users_with_negotiations': db.session.query(User.id).join(Negotiation).distinct().count(),
        'avg_orders_per_user': db.session.query(func.avg(func.count(Order.id))).join(User).group_by(User.id).scalar() or 0
    }
    
    return render_template('admin/reports/users.html',
                         registration_trends=registration_trends,
                         user_activity=user_activity,
                         top_customers=top_customers,
                         engagement_metrics=engagement_metrics)


@admin_bp.route('/reports/financial')
@login_required
@admin_required
def financial_reports():
    """Financial reports - profit margins, payment methods"""
    # Payment method analysis
    payment_methods = db.session.query(
        Payment.method,
        func.count(Payment.id).label('transactions'),
        func.sum(Payment.amount).label('total_amount'),
        func.avg(Payment.amount).label('avg_amount'),
        func.sum(case((Payment.status == 'success', Payment.amount), else_=0)).label('successful_amount')
    ).group_by(Payment.method).order_by(desc('total_amount')).all()
    
    # Monthly financial summary
    monthly_financial = db.session.query(
        func.strftime('%Y-%m', Payment.created_at).label('month'),
        func.count(Payment.id).label('transactions'),
        func.sum(Payment.amount).label('total_amount'),
        func.sum(case((Payment.status == 'success', Payment.amount), else_=0)).label('successful_amount'),
        func.sum(case((Payment.status == 'failed', Payment.amount), else_=0)).label('failed_amount')
    ).group_by(func.strftime('%Y-%m', Payment.created_at)).order_by('month').limit(12).all()
    
    # Revenue vs Negotiation analysis
    revenue_analysis = db.session.query(
        func.strftime('%Y-%m', Order.created_at).label('month'),
        func.sum(Order.price).label('direct_revenue'),
        func.sum(case((Negotiation.status == 'accepted', Negotiation.final_price), else_=0)).label('negotiated_revenue')
    ).outerjoin(Negotiation, Order.vehicle_id == Negotiation.vehicle_id).filter(
        Order.status == 'paid'
    ).group_by(func.strftime('%Y-%m', Order.created_at)).order_by('month').limit(12).all()
    
    # Financial summary
    financial_summary = {
        'total_revenue': db.session.query(func.sum(Order.price)).filter(Order.status == 'paid').scalar() or 0,
        'total_payments': db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'success').scalar() or 0,
        'failed_payments': db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'failed').scalar() or 0,
        'avg_payment_amount': db.session.query(func.avg(Payment.amount)).filter(Payment.status == 'success').scalar() or 0,
        'payment_success_rate': 0  # Will calculate below
    }
    
    # Calculate payment success rate
    total_payment_attempts = db.session.query(func.count(Payment.id)).scalar() or 0
    successful_payments = db.session.query(func.count(Payment.id)).filter(Payment.status == 'success').scalar() or 0
    if total_payment_attempts > 0:
        financial_summary['payment_success_rate'] = (successful_payments / total_payment_attempts) * 100
    
    return render_template('admin/reports/financial.html',
                         payment_methods=payment_methods,
                         monthly_financial=monthly_financial,
                         revenue_analysis=revenue_analysis,
                         financial_summary=financial_summary)


@admin_bp.route('/reports/export')
@login_required
@admin_required
def export_reports():
    """Export functionality for reports"""
    export_type = request.args.get('type', 'sales')  # sales, vehicles, users, financial
    format_type = request.args.get('format', 'csv')  # csv, pdf
    
    if export_type == 'sales':
        # Export sales data
        period = request.args.get('period', 'monthly')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if period == 'daily':
            data = db.session.query(
                func.date(Order.created_at).label('date'),
                func.count(Order.id).label('orders'),
                func.sum(Order.price).label('revenue'),
                func.avg(Order.price).label('avg_order_value')
            ).filter(
                Order.status == 'paid',
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            ).group_by(func.date(Order.created_at)).order_by('date').all()
            
        elif period == 'weekly':
            data = db.session.query(
                func.strftime('%Y-W%W', Order.created_at).label('week'),
                func.count(Order.id).label('orders'),
                func.sum(Order.price).label('revenue'),
                func.avg(Order.price).label('avg_order_value')
            ).filter(
                Order.status == 'paid',
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            ).group_by(func.strftime('%Y-W%W', Order.created_at)).order_by('week').all()
            
        else:  # monthly
            data = db.session.query(
                func.strftime('%Y-%m', Order.created_at).label('month'),
                func.count(Order.id).label('orders'),
                func.sum(Order.price).label('revenue'),
                func.avg(Order.price).label('avg_order_value')
            ).filter(
                Order.status == 'paid',
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            ).group_by(func.strftime('%Y-%m', Order.created_at)).order_by('month').all()
    
    elif export_type == 'vehicles':
        # Export vehicle performance data
        data = db.session.query(
            Vehicle.make, Vehicle.model, Vehicle.year,
            func.count(Order.id).label('orders'),
            func.sum(Order.price).label('revenue'),
            func.avg(Order.price).label('avg_price')
        ).outerjoin(Order, and_(Vehicle.id == Order.vehicle_id, Order.status == 'paid')).group_by(
            Vehicle.id, Vehicle.make, Vehicle.model, Vehicle.year
        ).order_by(desc('revenue')).all()
    
    elif export_type == 'users':
        # Export user analytics data
        data = db.session.query(
            User.name, User.email, User.created_at,
            func.count(Order.id).label('orders'),
            func.sum(Order.price).label('total_spent'),
            func.avg(Order.price).label('avg_order_value')
        ).outerjoin(Order, and_(User.id == Order.user_id, Order.status == 'paid')).group_by(
            User.id, User.name, User.email, User.created_at
        ).order_by(desc('total_spent')).all()
    
    elif export_type == 'financial':
        # Export financial data
        data = db.session.query(
            Payment.method, Payment.status,
            func.count(Payment.id).label('transactions'),
            func.sum(Payment.amount).label('total_amount'),
            func.avg(Payment.amount).label('avg_amount')
        ).group_by(Payment.method, Payment.status).order_by(desc('total_amount')).all()
    
    else:
        flash('Invalid export type.', 'error')
        return redirect(url_for('admin.reports_dashboard'))
    
    if format_type == 'csv':
        # Generate CSV response
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        if data:
            headers = list(data[0]._asdict().keys())
            writer.writerow(headers)
            
            # Write data
            for row in data:
                writer.writerow([getattr(row, header) for header in headers])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={export_type}_report_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
    
    else:  # PDF (placeholder for future implementation)
        flash('PDF export not yet implemented.', 'info')
        return redirect(url_for('admin.reports_dashboard'))
