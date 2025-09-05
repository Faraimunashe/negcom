#!/usr/bin/env python3
"""
Script to create an admin user for the AutoDeal platform.
Run this script to create an admin account.
"""

from app import create_app, db
from app.models import User
from passlib.hash import sha256_crypt

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        
        # Check if admin already exists
        existing_admin = User.query.filter_by(role=1).first()
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.email}")
            return
        
        # Create admin user
        admin_email = input("Enter admin email: ").strip()
        admin_name = input("Enter admin name: ").strip()
        admin_password = input("Enter admin password: ").strip()
        
        if not admin_email or not admin_name or not admin_password:
            print("All fields are required!")
            return
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            print("A user with this email already exists!")
            return
        
        try:
            # Create admin user
            password_hash = sha256_crypt.encrypt(admin_password)
            admin_user = User(
                email=admin_email,
                password=password_hash,
                name=admin_name,
                role=1  # 1 = admin
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"Admin user created successfully!")
            print(f"Email: {admin_email}")
            print(f"Name: {admin_name}")
            print(f"Role: Admin")
            print("\nYou can now log in to the admin panel at /admin")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin_user()
