from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc, asc
from app import db
from app.models import Vehicle, Negotiation, NegotiationOffer, User, VehicleImage, OfferByEnum, VehicleLocation, VehicleCondition
from app.forms import NegotiationForm, ContactSellerForm
from app.ml_negotiation import ml_engine
from app.notification_service import NotificationService
from datetime import datetime
import json

negotiations_bp = Blueprint('negotiations', __name__, url_prefix='/negotiations')

@negotiations_bp.route('/')
@login_required
def index():
    """View all negotiations for the current user"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get negotiations where user is the buyer
    negotiations = Negotiation.query.filter(
        Negotiation.user_id == current_user.id
    ).order_by(desc(Negotiation.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get first offer and vehicle images for each negotiation
    for negotiation in negotiations.items:
        first_offer = NegotiationOffer.query.filter_by(
            negotiation_id=negotiation.id
        ).order_by(asc(NegotiationOffer.created_at)).first()
        negotiation.first_offer = first_offer
        
        # Get vehicle images
        negotiation.vehicle.images = VehicleImage.query.filter_by(vehicle_id=negotiation.vehicle_id).all()
    
    return render_template('negotiations/index.html', negotiations=negotiations)

@negotiations_bp.route('/create/<int:vehicle_id>', methods=['GET', 'POST'])
@login_required
def create(vehicle_id):
    """Create a new negotiation for a vehicle"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    # Note: Since there's no seller_id field, we'll allow negotiations on any vehicle
    # In a real system, you might want to add seller_id or use a different approach
    
    # Check if negotiation already exists
    existing_negotiation = Negotiation.query.filter(
        and_(
            Negotiation.vehicle_id == vehicle_id,
            Negotiation.user_id == current_user.id,
            Negotiation.status.in_(['pending', 'ongoing'])
        )
    ).first()
    
    if existing_negotiation:
        flash('You already have an active negotiation for this vehicle.', 'info')
        return redirect(url_for('negotiations.detail', negotiation_id=existing_negotiation.id))
    
    form = NegotiationForm()
    
    if form.validate_on_submit():
        try:
            # Create negotiation
            negotiation = Negotiation(
                user_id=current_user.id,
                vehicle_id=vehicle_id,
                status='pending'  # Waiting for admin response
            )
            db.session.add(negotiation)
            db.session.flush()  # Get the ID
            
            # Create initial offer
            offer = NegotiationOffer(
                negotiation_id=negotiation.id,
                offer_by=OfferByEnum.BUYER,
                offer_price=form.offer_amount.data,
                reason=form.message.data or ''
            )
            db.session.add(offer)
            
            db.session.commit()
            
            # Create notification for user
            NotificationService.create_notification(
                user_id=current_user.id,
                title="Negotiation Submitted",
                message=f"Your offer of ${form.offer_amount.data:,.2f} for {vehicle.year} {vehicle.make} {vehicle.model} has been submitted. Waiting for admin response.",
                type="info",
                category="negotiation",
                action_url=url_for('negotiations.detail', negotiation_id=negotiation.id),
                related_id=negotiation.id,
                related_type="negotiation"
            )
            
            # Notify all admins about new negotiation
            admins = User.query.filter_by(role=1).all()
            for admin in admins:
                NotificationService.create_notification(
                    user_id=admin.id,
                    title="New Negotiation Received",
                    message=f"{current_user.name} made an offer of ${form.offer_amount.data:,.2f} for {vehicle.year} {vehicle.make} {vehicle.model}",
                    type="info",
                    category="negotiation",
                    action_url=url_for('admin.negotiation_detail', negotiation_id=negotiation.id),
                    related_id=negotiation.id,
                    related_type="negotiation"
                )
            
            flash('Your offer has been submitted! An admin will respond shortly.', 'success')
            return redirect(url_for('negotiations.detail', negotiation_id=negotiation.id))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating the negotiation. Please try again.', 'error')
    
    # Get vehicle images, location, and condition
    vehicle.images = VehicleImage.query.filter_by(vehicle_id=vehicle_id).all()
    vehicle_location = VehicleLocation.query.filter_by(vehicle_id=vehicle_id).first()
    vehicle_condition = VehicleCondition.query.filter_by(vehicle_id=vehicle_id).first()
    
    return render_template('negotiations/create.html', 
                         vehicle=vehicle, 
                         form=form,
                         vehicle_location=vehicle_location,
                         vehicle_condition=vehicle_condition)

@negotiations_bp.route('/<int:negotiation_id>')
@login_required
def detail(negotiation_id):
    """View detailed negotiation information"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        flash('You are not authorized to view this negotiation.', 'error')
        return redirect(url_for('negotiations.index'))
    
    # Get vehicle details
    vehicle = Vehicle.query.get(negotiation.vehicle_id)
    
    # Get vehicle images
    images = VehicleImage.query.filter_by(vehicle_id=vehicle.id).all()
    
    # Get all offers for this negotiation
    offers = NegotiationOffer.query.filter_by(negotiation_id=negotiation_id).order_by(asc(NegotiationOffer.created_at)).all()
    
    # Get buyer info
    buyer = User.query.get(negotiation.user_id)
    
    # Since there's no seller_id, we'll show the negotiation as buyer-only
    user_role = 'buyer'
    
    return render_template('negotiations/detail.html',
                         negotiation=negotiation,
                         vehicle=vehicle,
                         images=images,
                         offers=offers,
                         buyer=buyer,
                         user_role=user_role)

@negotiations_bp.route('/<int:negotiation_id>/offer', methods=['POST'])
@login_required
def make_offer(negotiation_id):
    """Make a new offer in an existing negotiation"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Check if negotiation is still active
    if negotiation.status != 'ongoing':
        return jsonify({'success': False, 'message': 'Negotiation is no longer active'}), 400
    
    data = request.get_json()
    amount = float(data.get('amount', 0))
    message = data.get('message', '')
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid offer amount'}), 400
    
    try:
        # Create new offer (only buyers can make offers in this model)
        offer = NegotiationOffer(
            negotiation_id=negotiation_id,
            offer_by=OfferByEnum.BUYER,
            offer_price=amount,
            reason=message
        )
        db.session.add(offer)
        
        # Set negotiation to ongoing (waiting for admin response)
        negotiation.status = 'ongoing'
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify admins about new offer
        admins = User.query.filter_by(role=1).all()
        for admin in admins:
            NotificationService.create_notification(
                user_id=admin.id,
                title="New Offer in Negotiation",
                message=f"{current_user.name} made a new offer of ${amount:,.2f} in negotiation #{negotiation_id}",
                type="info",
                category="negotiation",
                action_url=url_for('admin.negotiation_detail', negotiation_id=negotiation_id),
                related_id=negotiation_id,
                related_type="negotiation"
            )
        
        return jsonify({
            'success': True,
            'message': 'Offer submitted successfully. Waiting for admin response.',
            'offer': {
                'id': offer.id,
                'amount': float(offer.offer_price),
                'message': offer.reason,
                'offered_by': offer.offer_by.value,
                'created_at': offer.created_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@negotiations_bp.route('/<int:negotiation_id>/accept', methods=['POST'])
@login_required
def accept_offer(negotiation_id):
    """Accept the latest offer in a negotiation"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Note: Since there's no seller_id, we'll allow any user to accept offers
    # In a real system, you might want to add proper seller authorization
    
    # Check if negotiation is active
    if negotiation.status != 'ongoing':
        return jsonify({'success': False, 'message': 'Negotiation is not active'}), 400
    
    try:
        # Get the latest offer
        latest_offer = NegotiationOffer.query.filter_by(
            negotiation_id=negotiation_id
        ).order_by(desc(NegotiationOffer.created_at)).first()
        
        if not latest_offer:
            return jsonify({'success': False, 'message': 'No offers found'}), 400
        
        # Update negotiation status
        negotiation.status = 'accepted'
        negotiation.final_price = latest_offer.offer_price
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Offer accepted successfully',
            'final_price': float(negotiation.final_price)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@negotiations_bp.route('/<int:negotiation_id>/reject', methods=['POST'])
@login_required
def reject_negotiation(negotiation_id):
    """Reject a negotiation"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        # Update negotiation status
        negotiation.status = 'rejected'
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Negotiation rejected successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@negotiations_bp.route('/<int:negotiation_id>/counter', methods=['POST'])
@login_required
def counter_offer(negotiation_id):
    """Make a counter offer"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Check if negotiation is active
    if negotiation.status != 'ongoing':
        return jsonify({'success': False, 'message': 'Negotiation is not active'}), 400
    
    data = request.get_json()
    amount = float(data.get('amount', 0))
    message = data.get('message', '')
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid offer amount'}), 400
    
    try:
        # Create counter offer (only buyers can make offers in this model)
        offer = NegotiationOffer(
            negotiation_id=negotiation_id,
            offer_by=OfferByEnum.BUYER,
            offer_price=amount,
            reason=message
        )
        db.session.add(offer)
        
        # Set negotiation to ongoing (waiting for admin response)
        negotiation.status = 'ongoing'
        negotiation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify user about their counter offer
        vehicle = Vehicle.query.get(negotiation.vehicle_id)
        NotificationService.create_notification(
            user_id=current_user.id,
            title="Counter Offer Submitted",
            message=f"Your counter offer of ${amount:,.2f} for {vehicle.year} {vehicle.make} {vehicle.model} has been submitted. Waiting for admin response.",
            type="info",
            category="negotiation",
            action_url=url_for('negotiations.detail', negotiation_id=negotiation.id),
            related_id=negotiation.id,
            related_type="negotiation"
        )
        
        # Notify admins about counter offer
        admins = User.query.filter_by(role=1).all()
        for admin in admins:
            NotificationService.create_notification(
                user_id=admin.id,
                title="Counter Offer Received",
                message=f"{current_user.name} made a counter offer of ${amount:,.2f} in negotiation #{negotiation_id}",
                type="info",
                category="negotiation",
                action_url=url_for('admin.negotiation_detail', negotiation_id=negotiation_id),
                related_id=negotiation_id,
                related_type="negotiation"
            )
        
        return jsonify({
            'success': True,
            'message': 'Counter offer submitted successfully. Waiting for admin response.',
            'offer': {
                'id': offer.id,
                'amount': float(offer.offer_price),
                'message': offer.reason,
                'offered_by': offer.offer_by.value,
                'created_at': offer.created_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@negotiations_bp.route('/my-offers')
@login_required
def my_offers():
    """View negotiations where user is the buyer"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    negotiations = Negotiation.query.filter_by(user_id=current_user.id).order_by(
        desc(Negotiation.updated_at)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get first offer and vehicle images for each negotiation
    for negotiation in negotiations.items:
        first_offer = NegotiationOffer.query.filter_by(
            negotiation_id=negotiation.id
        ).order_by(asc(NegotiationOffer.created_at)).first()
        negotiation.first_offer = first_offer
        
        # Get vehicle images
        negotiation.vehicle.images = VehicleImage.query.filter_by(vehicle_id=negotiation.vehicle_id).all()
    
    return render_template('negotiations/my_offers.html', negotiations=negotiations)

@negotiations_bp.route('/received-offers')
@login_required
def received_offers():
    """View negotiations where user is the seller"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Note: Since there's no seller_id field, this will show all negotiations
    # In a real system, you might want to add proper seller filtering
    negotiations = Negotiation.query.order_by(desc(Negotiation.updated_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get first offer and vehicle images for each negotiation
    for negotiation in negotiations.items:
        first_offer = NegotiationOffer.query.filter_by(
            negotiation_id=negotiation.id
        ).order_by(asc(NegotiationOffer.created_at)).first()
        negotiation.first_offer = first_offer
        
        # Get vehicle images
        negotiation.vehicle.images = VehicleImage.query.filter_by(vehicle_id=negotiation.vehicle_id).all()
    
    return render_template('negotiations/received_offers.html', negotiations=negotiations)

@negotiations_bp.route('/<int:negotiation_id>/contact', methods=['GET', 'POST'])
@login_required
def contact(negotiation_id):
    """Contact the other party in a negotiation"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        flash('You are not authorized to contact in this negotiation.', 'error')
        return redirect(url_for('negotiations.index'))
    
    # Note: Since there's no seller_id, we'll show a generic contact form
    # In a real system, you might want to add proper seller identification
    other_party = None
    
    # Get first offer for this negotiation
    first_offer = NegotiationOffer.query.filter_by(
        negotiation_id=negotiation.id
    ).order_by(asc(NegotiationOffer.created_at)).first()
    negotiation.first_offer = first_offer
    
    form = ContactSellerForm()
    
    if form.validate_on_submit():
        # Here you would typically send an email or create a message
        # For now, we'll just show a success message
        flash(f'Your message has been sent to {other_party.name}.', 'success')
        return redirect(url_for('negotiations.detail', negotiation_id=negotiation_id))
    
    return render_template('negotiations/contact.html',
                         negotiation=negotiation,
                         other_party=other_party,
                         form=form)

@negotiations_bp.route('/api/status/<int:negotiation_id>')
@login_required
def api_status(negotiation_id):
    """API endpoint to get negotiation status"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get latest offer
    latest_offer = NegotiationOffer.query.filter_by(
        negotiation_id=negotiation_id
    ).order_by(desc(NegotiationOffer.created_at)).first()
    
    return jsonify({
        'success': True,
        'negotiation': {
            'id': negotiation.id,
            'status': negotiation.status,
            'final_price': float(negotiation.final_price) if negotiation.final_price else None,
            'updated_at': negotiation.updated_at.isoformat()
        },
        'latest_offer': {
            'id': latest_offer.id,
            'amount': float(latest_offer.offer_price),
            'offered_by': latest_offer.offer_by.value,
            'reason': latest_offer.reason,
            'created_at': latest_offer.created_at.isoformat()
        } if latest_offer else None
    })

@negotiations_bp.route('/api/predict/<int:vehicle_id>', methods=['POST'])
@login_required
def predict_negotiation(vehicle_id):
    """API endpoint to predict negotiation outcome using ML"""
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    
    data = request.get_json()
    offer_amount = float(data.get('offer_amount', 0))
    
    if offer_amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid offer amount'}), 400
    
    try:
        # Get ML prediction
        prediction = ml_engine.predict_negotiation_outcome(
            current_user.id, vehicle_id, offer_amount
        )
        
        if not prediction:
            return jsonify({'success': False, 'message': 'Prediction failed'}), 500
        
        # Generate AI counter offer
        ai_response = ml_engine.generate_ai_counter_offer(
            current_user.id, vehicle_id, offer_amount
        )
        
        return jsonify({
            'success': True,
            'prediction': {
                'predicted_price': prediction['predicted_price'],
                'predicted_outcome': prediction['predicted_outcome'],
                'outcome_probability': prediction['outcome_probability'],
                'customer_rating': prediction['customer_rating']
            },
            'ai_response': ai_response,
            'vehicle_price': float(vehicle.price),
            'offer_percentage': (offer_amount / float(vehicle.price)) * 100
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@negotiations_bp.route('/api/ai-counter/<int:negotiation_id>', methods=['POST'])
@login_required
def ai_counter_offer(negotiation_id):
    """Generate AI counter offer for existing negotiation"""
    negotiation = Negotiation.query.get_or_404(negotiation_id)
    
    # Check if user is part of this negotiation
    if negotiation.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get latest customer offer
    latest_offer = NegotiationOffer.query.filter_by(
        negotiation_id=negotiation_id,
        offer_by=OfferByEnum.BUYER
    ).order_by(desc(NegotiationOffer.created_at)).first()
    
    if not latest_offer:
        return jsonify({'success': False, 'message': 'No customer offer found'}), 400
    
    try:
        # Generate AI counter offer
        ai_response = ml_engine.generate_ai_counter_offer(
            current_user.id, negotiation.vehicle_id, float(latest_offer.offer_price)
        )
        
        if ai_response and ai_response['type'] in ['counter', 'suggest']:
            # Create AI counter offer
            ai_offer = NegotiationOffer(
                negotiation_id=negotiation_id,
                offer_by=OfferByEnum.AI,
                offer_price=ai_response['price'],
                reason=ai_response['message']
            )
            db.session.add(ai_offer)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'ai_offer': {
                    'id': ai_offer.id,
                    'amount': float(ai_offer.offer_price),
                    'message': ai_offer.reason,
                    'offered_by': ai_offer.offer_by.value,
                    'created_at': ai_offer.created_at.isoformat()
                },
                'confidence': ai_response['confidence']
            })
        else:
            return jsonify({
                'success': True,
                'ai_response': ai_response,
                'no_counter': True
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
