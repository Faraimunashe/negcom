from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_login import login_user, logout_user, login_required, current_user
from passlib.hash import sha256_crypt
from . import db
from app.forms import *
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def index():
    """Home page - redirect to login or dashboard based on auth status"""
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == 1:  # Admin
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        # Redirect authenticated users based on role
        if current_user.role == 1:  # Admin
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        password = form.password.data
        
        user = User.query.filter_by(email=email).first()
        
        if user and sha256_crypt.verify(password, user.password):
            login_user(user, remember=True)
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            
            flash(f'Welcome back, {user.name}!', 'success')
            
            # Redirect to next page if specified
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Redirect based on user role
            if user.role == 1:  # Admin
                return redirect(url_for('admin.dashboard'))
            else:  # Regular user
                return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('auth/login.html', form=form, title='Sign In')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == 1:  # Admin
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.lower().strip()
        password = form.password.data
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists. Please sign in instead.', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            # Create new user
            password_hash = sha256_crypt.hash(password)
            new_user = User(email=email, password=password_hash, name=name, role=2)  # role=2 for regular user
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully! Please sign in to continue.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form, title='Create Account')

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """User logout"""
    user_name = current_user.name
    logout_user()
    session.clear()
    flash(f'You have been logged out successfully. Goodbye, {user_name}!', 'success')
    return redirect(url_for('auth.login'))