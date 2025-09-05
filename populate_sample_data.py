#!/usr/bin/env python3
"""
Script to populate the database with sample vehicle data for testing the browse functionality.
Run this script after creating the database tables.
"""

from app import create_app, db
from app.models import User, Vehicle, VehicleImage, Category, VehicleCategory
from datetime import datetime
import random

def create_sample_data():
    app = create_app()
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Check if vehicles already exist
        if Vehicle.query.first():
            print("Sample vehicles already exist. Skipping...")
            return
        
        print("Creating sample vehicles...")
        
        # Sample vehicle data - using only fields that exist in the Vehicle model
        vehicles_data = [
            {
                "make": "Toyota",
                "model": "Camry",
                "year": 2020,
                "price": 25000.00,
                "mileage": 35000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "Silver"
            },
            {
                "make": "Honda",
                "model": "Civic",
                "year": 2019,
                "price": 22000.00,
                "mileage": 42000,
                "engine_type": "petrol",
                "transmission": "manual",
                "body_type": "Sedan",
                "color": "Blue"
            },
            {
                "make": "Ford",
                "model": "F-150",
                "year": 2021,
                "price": 45000.00,
                "mileage": 28000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Truck",
                "color": "Black"
            },
            {
                "make": "BMW",
                "model": "3 Series",
                "year": 2020,
                "price": 38000.00,
                "mileage": 31000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "White"
            },
            {
                "make": "Tesla",
                "model": "Model 3",
                "year": 2022,
                "price": 52000.00,
                "mileage": 15000,
                "engine_type": "electric",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "Red"
            },
            {
                "make": "Audi",
                "model": "A4",
                "year": 2019,
                "price": 32000.00,
                "mileage": 45000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "Gray"
            },
            {
                "make": "Mercedes-Benz",
                "model": "C-Class",
                "year": 2021,
                "price": 42000.00,
                "mileage": 25000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "Black"
            },
            {
                "make": "Nissan",
                "model": "Altima",
                "year": 2020,
                "price": 24000.00,
                "mileage": 38000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "White"
            },
            {
                "make": "Chevrolet",
                "model": "Silverado",
                "year": 2020,
                "price": 40000.00,
                "mileage": 35000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Truck",
                "color": "Blue"
            },
            {
                "make": "Hyundai",
                "model": "Elantra",
                "year": 2021,
                "price": 20000.00,
                "mileage": 22000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "Sedan",
                "color": "Silver"
            },
            {
                "make": "Subaru",
                "model": "Outback",
                "year": 2020,
                "price": 28000.00,
                "mileage": 40000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "SUV",
                "color": "Green"
            },
            {
                "make": "Lexus",
                "model": "RX",
                "year": 2021,
                "price": 48000.00,
                "mileage": 18000,
                "engine_type": "petrol",
                "transmission": "automatic",
                "body_type": "SUV",
                "color": "White"
            }
        ]
        
        vehicles = []
        for vehicle_data in vehicles_data:
            vehicle = Vehicle(**vehicle_data)
            vehicles.append(vehicle)
            db.session.add(vehicle)
        
        db.session.commit()
        print("Created sample vehicles")
        
        # Create sample vehicle images
        image_urls = [
            "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1549317336-206569e8475c?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1544636331-e26879cd4d9b?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1555215695-3004980ad54e?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1563720223185-11003d516935?w=800&h=600&fit=crop",
            "https://images.unsplash.com/photo-1544829099-b9a0cccf1c38?w=800&h=600&fit=crop"
        ]
        
        for i, vehicle in enumerate(vehicles):
            # Add 1-3 random images per vehicle
            num_images = random.randint(1, 3)
            for j in range(num_images):
                image_url = random.choice(image_urls)
                is_primary = j == 0  # First image is primary
                vehicle_image = VehicleImage(
                    vehicle_id=vehicle.id,
                    image_url=image_url,
                    is_primary=is_primary
                )
                db.session.add(vehicle_image)
        
        db.session.commit()
        print("Created sample vehicle images")
        
        # Create vehicle-category relationships (assuming categories exist)
        categories = Category.query.all()
        if categories:
            for vehicle in vehicles:
                # Assign 1-2 random categories to each vehicle
                num_categories = random.randint(1, 2)
                selected_categories = random.sample(categories, min(num_categories, len(categories)))
                
                for category in selected_categories:
                    vehicle_category = VehicleCategory(
                        vehicle_id=vehicle.id,
                        category_id=category.id
                    )
                    db.session.add(vehicle_category)
            
            db.session.commit()
            print("Created vehicle-category relationships")
        
        print("Sample data creation completed successfully!")
        print(f"Created {len(vehicles)} vehicles with images")

if __name__ == "__main__":
    create_sample_data()