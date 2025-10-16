from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, asc
from app import db
from app.models import Order, Payment, Vehicle, User, VehicleImage, OrderDelivery, OrderRating
from app.forms import PaymentForm, DeliveryAddressForm, OrderRatingForm
from app.notification_service import NotificationService
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
    
    # Get orders for current user with vehicle information
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
        
        # Create notification for order creation
        NotificationService.create_notification(
            user_id=current_user.id,
            title="Order Created",
            message=f"Your order #{order.id} has been created for {vehicle.year} {vehicle.make} {vehicle.model} - ${order.price:,.2f}. Please provide delivery details and complete payment.",
            type="success",
            category="order",
            action_url=url_for('orders.payment', order_id=order.id),
            related_id=order.id,
            related_type="order"
        )
        
        flash('Order created successfully! Please provide delivery address and payment details.', 'success')
        return redirect(url_for('orders.payment', order_id=order.id))
        
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
    
    # Get delivery information
    delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
    
    # Get rating information
    rating = OrderRating.query.filter_by(order_id=order_id).first()
    
    return render_template('orders/detail.html',
                         order=order,
                         vehicle=vehicle,
                         images=images,
                         payment=payment,
                         delivery=delivery,
                         rating=rating)

@orders_bp.route('/<int:order_id>/payment', methods=['GET', 'POST'])
@login_required
def payment(order_id):
    """Process payment for an order with delivery address"""
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
    
    # Check if delivery info exists
    existing_delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
    
    payment_form = PaymentForm()
    delivery_form = DeliveryAddressForm()
    
    if request.method == 'POST' and payment_form.validate_on_submit() and (existing_delivery or delivery_form.validate_on_submit()):
        try:
            # Create delivery information if not exists
            if not existing_delivery:
                delivery = OrderDelivery(
                    order_id=order_id,
                    address=delivery_form.address.data,
                    city=delivery_form.city.data,
                    status='pending'
                )
                db.session.add(delivery)
            
            # Generate unique payment reference
            payment_reference = f"PAY-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Create payment record
            payment = Payment(
                order_id=order_id,
                amount=order.price,
                method=payment_form.payment_method.data,
                reference=payment_reference,
                status='pending'
            )
            db.session.add(payment)
            
            # Simulate payment processing (in real app, integrate with payment gateway)
            if simulate_payment_processing(payment_form.payment_method.data):
                payment.status = 'success'
                order.status = 'paid'
                
                # Create payment success notification
                delivery_city = existing_delivery.city if existing_delivery else delivery_form.city.data
                NotificationService.create_notification(
                    user_id=current_user.id,
                    title="Payment Successful",
                    message=f"Your payment of ${payment.amount:,.2f} for order #{order.id} has been processed successfully! Delivery to {delivery_city}.",
                    type="success",
                    category="order",
                    action_url=url_for('orders.detail', order_id=order.id),
                    related_id=order.id,
                    related_type="order"
                )
                
                flash('Payment successful! Your order has been confirmed.', 'success')
            else:
                payment.status = 'failed'
                
                # Create payment failure notification
                NotificationService.create_notification(
                    user_id=current_user.id,
                    title="Payment Failed",
                    message=f"Your payment of ${payment.amount:,.2f} for order #{order.id} failed. Please try again.",
                    type="error",
                    category="order",
                    action_url=url_for('orders.payment', order_id=order.id),
                    related_id=order.id,
                    related_type="order"
                )
                
                flash('Payment failed. Please try again.', 'error')
            
            db.session.commit()
            return redirect(url_for('orders.detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing payment: {str(e)}', 'error')
    
    # Get vehicle for display
    vehicle = Vehicle.query.get(order.vehicle_id)
    images = VehicleImage.query.filter_by(vehicle_id=vehicle.id).all()
    
    return render_template('orders/payment.html', 
                         order=order, 
                         vehicle=vehicle,
                         images=images,
                         payment_form=payment_form, 
                         delivery_form=delivery_form,
                         existing_delivery=existing_delivery)

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

@orders_bp.route('/<int:order_id>/rate', methods=['GET', 'POST'])
@login_required
def rate_order(order_id):
    """Rate a completed order"""
    order = Order.query.get_or_404(order_id)
    
    # Check if user is authorized
    if order.user_id != current_user.id:
        flash('You are not authorized to rate this order.', 'error')
        return redirect(url_for('orders.index'))
    
    # Check if order is paid/completed
    if order.status != 'paid':
        flash('You can only rate completed orders.', 'error')
        return redirect(url_for('orders.detail', order_id=order_id))
    
    # Check if already rated
    existing_rating = OrderRating.query.filter_by(order_id=order_id).first()
    if existing_rating:
        flash('You have already rated this order.', 'info')
        return redirect(url_for('orders.detail', order_id=order_id))
    
    form = OrderRatingForm()
    
    if form.validate_on_submit():
        try:
            # Create rating
            rating = OrderRating(
                order_id=order_id,
                rating=int(form.rating.data),
                comment=form.comment.data
            )
            db.session.add(rating)
            
            # Update delivery status to delivered if not already
            delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
            if delivery and delivery.status != 'delivered':
                delivery.status = 'delivered'
            
            db.session.commit()
            
            # Create notification
            NotificationService.create_notification(
                user_id=current_user.id,
                title="Rating Submitted",
                message=f"Thank you for rating order #{order.id}! Your feedback helps us improve.",
                type="success",
                category="order",
                action_url=url_for('orders.detail', order_id=order.id),
                related_id=order.id,
                related_type="order"
            )
            
            flash('Thank you for rating your order!', 'success')
            return redirect(url_for('orders.detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting your rating.', 'error')
    
    # Get vehicle details for display
    vehicle = order.vehicle
    
    return render_template('orders/rate.html', order=order, vehicle=vehicle, form=form)

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
