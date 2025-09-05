from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, asc
from app import db
from app.models import Order, Payment, Vehicle, User, VehicleImage
from app.forms import PaymentForm
from datetime import datetime
import uuid
import random

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/')
@login_required
def index():
    """View all orders for the current user"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get orders for current user
    orders = Order.query.filter_by(user_id=current_user.id).order_by(
        desc(Order.created_at)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('orders/index.html', orders=orders)

@orders_bp.route('/create/<int:vehicle_id>')
@login_required
def create(vehicle_id):
    """Create a new order for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Check if user already has an order for this vehicle
    existing_order = Order.query.filter(
        Order.user_id == current_user.id,
        Order.vehicle_id == vehicle_id,
        Order.status.in_(['pending', 'paid'])
    ).first()
    
    if existing_order:
        flash('You already have an order for this vehicle.', 'info')
        return redirect(url_for('orders.detail', order_id=existing_order.id))
    
    try:
        # Create new order
        order = Order(
            user_id=current_user.id,
            vehicle_id=vehicle_id,
            price=vehicle.price,
            status='pending'
        )
        db.session.add(order)
        db.session.commit()
        
        flash('Order created successfully! Please proceed to payment.', 'success')
        return redirect(url_for('orders.detail', order_id=order.id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating the order.', 'error')
        return redirect(url_for('vehicles.detail', vehicle_id=vehicle_id))

@orders_bp.route('/create-from-negotiation/<int:negotiation_id>')
@login_required
def create_from_negotiation(negotiation_id):
    """Create an order from an accepted negotiation"""
    from app.models import Negotiation
    
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is authorized
    if negotiation.user_id != current_user.id:
        flash('You are not authorized to create an order for this negotiation.', 'error')
        return redirect(url_for('negotiations.index'))
    
    # Check if negotiation is accepted
    if negotiation.status != 'accepted':
        flash('This negotiation has not been accepted yet.', 'error')
        return redirect(url_for('negotiations.detail', negotiation_id=negotiation_id))
    
    # Check if order already exists
    existing_order = Order.query.filter(
        Order.user_id == current_user.id,
        Order.vehicle_id == negotiation.vehicle_id,
        Order.status.in_(['pending', 'paid'])
    ).first()
    
    if existing_order:
        flash('You already have an order for this vehicle.', 'info')
        return redirect(url_for('orders.detail', order_id=existing_order.id))
    
    try:
        # Create order with negotiated price
        order = Order(
            user_id=current_user.id,
            vehicle_id=negotiation.vehicle_id,
            price=negotiation.final_price or negotiation.vehicle.price,
            status='pending'
        )
        db.session.add(order)
        db.session.commit()
        
        flash('Order created from negotiation! Please proceed to payment.', 'success')
        return redirect(url_for('orders.detail', order_id=order.id))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating the order.', 'error')
        return redirect(url_for('negotiations.detail', negotiation_id=negotiation_id))

@orders_bp.route('/<int:order_id>')
@login_required
def detail(order_id):
    """View detailed order information"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user is authorized
    if order.user_id != current_user.id:
        flash('You are not authorized to view this order.', 'error')
        return redirect(url_for('orders.index'))
    
    # Get vehicle details
    vehicle = Vehicle.query.get(order.vehicle_id)
    images = VehicleImage.query.filter_by(vehicle_id=vehicle.id).all()
    
    # Get payment information
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    return render_template('orders/detail.html',
                         order=order,
                         vehicle=vehicle,
                         images=images,
                         payment=payment)

@orders_bp.route('/<int:order_id>/payment', methods=['GET', 'POST'])
@login_required
def payment(order_id):
    """Process payment for an order"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user is authorized
    if order.user_id != current_user.id:
        flash('You are not authorized to pay for this order.', 'error')
        return redirect(url_for('orders.index'))
    
    # Check if order is pending
    if order.status != 'pending':
        flash('This order cannot be paid for.', 'error')
        return redirect(url_for('orders.detail', order_id=order_id))
    
    # Check if payment already exists
    existing_payment = Payment.query.filter_by(order_id=order_id).first()
    if existing_payment:
        flash('Payment already exists for this order.', 'info')
        return redirect(url_for('orders.detail', order_id=order_id))
    
    form = PaymentForm()
    
    if form.validate_on_submit():
        try:
            # Generate unique payment reference
            payment_reference = f"PAY-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Create payment record
            payment = Payment(
                order_id=order_id,
                amount=order.price,
                method=form.payment_method.data,
                reference=payment_reference,
                status='pending'
            )
            db.session.add(payment)
            
            # Simulate payment processing (in real app, integrate with payment gateway)
            if simulate_payment_processing(form.payment_method.data):
                payment.status = 'success'
                order.status = 'paid'
                flash('Payment successful! Your order has been confirmed.', 'success')
            else:
                payment.status = 'failed'
                flash('Payment failed. Please try again.', 'error')
            
            db.session.commit()
            return redirect(url_for('orders.detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while processing payment.', 'error')
    
    return render_template('orders/payment.html', order=order, form=form)

@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel(order_id):
    """Cancel an order"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user is authorized
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Check if order can be cancelled
    if order.status not in ['pending']:
        return jsonify({'success': False, 'message': 'Order cannot be cancelled'}), 400
    
    try:
        # Update order status
        order.status = 'failed'
        
        # If payment exists, mark it as failed
        payment = Payment.query.filter_by(order_id=order_id).first()
        if payment and payment.status == 'pending':
            payment.status = 'failed'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Order cancelled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@orders_bp.route('/api/status/<int:order_id>')
@login_required
def api_status(order_id):
    """API endpoint to get order status"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user is authorized
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get payment info
    payment = Payment.query.filter_by(order_id=order_id).first()
    
    return jsonify({
        'success': True,
        'order': {
            'id': order.id,
            'status': order.status,
            'price': float(order.price),
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat()
        },
        'payment': {
            'id': payment.id,
            'status': payment.status,
            'method': payment.method,
            'reference': payment.reference,
            'amount': float(payment.amount),
            'created_at': payment.created_at.isoformat()
        } if payment else None
    })

def simulate_payment_processing(payment_method):
    """Simulate payment processing (replace with real payment gateway integration)"""
    # Simulate different success rates based on payment method
    success_rates = {
        'credit_card': 0.95,
        'paypal': 0.98,
        'bank_transfer': 0.90,
        'mobile_money': 0.85
    }
    
    success_rate = success_rates.get(payment_method, 0.90)
    return random.random() < success_rate
