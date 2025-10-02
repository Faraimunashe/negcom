from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, desc, asc
from app import db
from app.models import Vehicle, VehicleImage, Category, VehicleCategory, User
from app.forms import VehicleSearchForm, VehicleFilterForm
import os

vehicles_bp = Blueprint('vehicles', __name__, url_prefix='/vehicles')

@vehicles_bp.route('/')
def browse():
    """Browse all vehicles with pagination and basic filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Get filter parameters
    search_query = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
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
                Vehicle.body_type.ilike(f'%{search_query}%')
            )
        )
    
    # Apply category filter
    if category_id:
        query = query.join(VehicleCategory).filter(VehicleCategory.category_id == category_id)
    
    # Apply price filters
    if min_price:
        query = query.filter(Vehicle.price >= min_price)
    if max_price:
        query = query.filter(Vehicle.price <= max_price)
    
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
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.created_at))
        else:
            query = query.order_by(desc(Vehicle.created_at))
    
    # Paginate results
    vehicles = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get images for each vehicle
    for vehicle in vehicles.items:
        vehicle.images = VehicleImage.query.filter_by(vehicle_id=vehicle.id).all()
    
    # Get categories for filter dropdown
    categories = Category.query.all()
    
    # Get price range for filter
    price_range = db.session.query(
        db.func.min(Vehicle.price).label('min_price'),
        db.func.max(Vehicle.price).label('max_price')
    ).first()
    
    return render_template('vehicles/browse.html',
                         vehicles=vehicles,
                         categories=categories,
                         price_range=price_range,
                         search_query=search_query,
                         category_id=category_id,
                         min_price=min_price,
                         max_price=max_price,
                         sort_by=sort_by,
                         sort_order=sort_order)

@vehicles_bp.route('/<int:vehicle_id>')
def detail(vehicle_id):
    """View detailed information about a specific vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Vehicle availability check can be added here if needed
    
    # Get vehicle images
    image_objects = VehicleImage.query.filter_by(vehicle_id=vehicle_id).all()
    # Convert to serializable format for JavaScript
    images = [{'id': img.id, 'url': url_for('static', filename=img.image_url), 'is_primary': img.is_primary} for img in image_objects]
    
    # Get vehicle categories
    vehicle_categories = db.session.query(Category).join(VehicleCategory).filter(
        VehicleCategory.vehicle_id == vehicle_id
    ).all()
    
    # Get related vehicles (same category, different vehicle)
    related_vehicles = []
    if vehicle_categories:
        category_ids = [cat.id for cat in vehicle_categories]
        related_vehicles = Vehicle.query.join(VehicleCategory).filter(
            and_(
                VehicleCategory.category_id.in_(category_ids),
                Vehicle.id != vehicle_id,
            )
        ).limit(4).all()
        
        # Get images for related vehicles
        for related_vehicle in related_vehicles:
            related_vehicle.images = VehicleImage.query.filter_by(vehicle_id=related_vehicle.id).all()
    
    return render_template('vehicles/detail.html',
                         vehicle=vehicle,
                         images=images,
                         image_objects=image_objects,  # Keep original objects for template display
                         categories=vehicle_categories,
                         related_vehicles=related_vehicles)

@vehicles_bp.route('/search')
def search():
    """Advanced search page with detailed filters"""
    form = VehicleSearchForm()
    filter_form = VehicleFilterForm()
    
    # Get all categories for filter form
    categories = Category.query.all()
    filter_form.category.choices = [(0, 'All Categories')] + [(cat.id, cat.name) for cat in categories]
    
    return render_template('vehicles/search.html',
                         form=form,
                         filter_form=filter_form,
                         categories=categories)

@vehicles_bp.route('/api/search')
def api_search():
    """API endpoint for AJAX search with filters"""
    search_query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    min_mileage = request.args.get('min_mileage', type=int)
    max_mileage = request.args.get('max_mileage', type=int)
    fuel_type = request.args.get('fuel_type', '')
    transmission = request.args.get('transmission', '')
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
                Vehicle.body_type.ilike(f'%{search_query}%')
            )
        )
    
    # Apply category filter
    if category_id:
        query = query.join(VehicleCategory).filter(VehicleCategory.category_id == category_id)
    
    # Apply price filters
    if min_price:
        query = query.filter(Vehicle.price >= min_price)
    if max_price:
        query = query.filter(Vehicle.price <= max_price)
    
    # Apply year filters
    if min_year:
        query = query.filter(Vehicle.year >= min_year)
    if max_year:
        query = query.filter(Vehicle.year <= max_year)
    
    # Apply mileage filters
    if min_mileage:
        query = query.filter(Vehicle.mileage >= min_mileage)
    if max_mileage:
        query = query.filter(Vehicle.mileage <= max_mileage)
    
    # Apply fuel type filter
    if fuel_type:
        query = query.filter(Vehicle.engine_type == fuel_type)
    
    # Apply transmission filter
    if transmission:
        query = query.filter(Vehicle.transmission == transmission)
    
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
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(asc(Vehicle.created_at))
        else:
            query = query.order_by(desc(Vehicle.created_at))
    
    # Get results
    vehicles = query.limit(50).all()
    
    # Convert to JSON
    results = []
    for vehicle in vehicles:
        # Get primary image
        primary_image = VehicleImage.query.filter_by(
            vehicle_id=vehicle.id, is_primary=True
        ).first()
        
        image_url = url_for('static', filename=primary_image.image_url) if primary_image else url_for('static', filename='images/no-image.svg')
        
        results.append({
            'id': vehicle.id,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.year,
            'price': float(vehicle.price),
            'mileage': vehicle.mileage,
            'engine_type': vehicle.engine_type,
            'transmission': vehicle.transmission,
            'image_url': image_url,
            'created_at': vehicle.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'vehicles': results,
        'total': len(results)
    })

@vehicles_bp.route('/category/<int:category_id>')
def category(category_id):
    """Browse vehicles by category"""
    category = Category.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Get vehicles in this category
    vehicles = Vehicle.query.join(VehicleCategory).filter(
        VehicleCategory.category_id == category_id,
    ).order_by(desc(Vehicle.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('vehicles/category.html',
                         category=category,
                         vehicles=vehicles)

@vehicles_bp.route('/favorites')
@login_required
def favorites():
    """View user's favorite vehicles"""
    # This would require a Favorites model - for now, return empty
    flash('Favorites feature coming soon!', 'info')
    return redirect(url_for('vehicles.browse'))

@vehicles_bp.route('/compare')
@login_required
def compare():
    """Compare selected vehicles"""
    vehicle_ids = request.args.getlist('vehicles')
    
    if len(vehicle_ids) < 2:
        flash('Please select at least 2 vehicles to compare.', 'error')
        return redirect(url_for('vehicles.browse'))
    
    if len(vehicle_ids) > 4:
        flash('You can compare up to 4 vehicles at once.', 'error')
        return redirect(url_for('vehicles.browse'))
    
    # Get vehicles
    vehicles = Vehicle.query.filter(
        Vehicle.id.in_(vehicle_ids),
    ).all()
    
    if len(vehicles) != len(vehicle_ids):
        flash('Some selected vehicles are no longer available.', 'error')
        return redirect(url_for('vehicles.browse'))
    
    return render_template('vehicles/compare.html', vehicles=vehicles)
