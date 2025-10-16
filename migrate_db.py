#!/usr/bin/env python3
"""
Database Migration Script
Creates new tables for: OrderDelivery, VehicleLocation, OrderRating, VehicleCondition

Note: The app automatically runs db.create_all() on startup, so new tables will be
created automatically. This script is provided as a standalone option if needed.
"""

from app import create_app, db

def migrate_database():
    """Create the new tables in the database"""
    app = create_app()
    
    with app.app_context():
        print("Starting database migration...")
        print("Creating new tables...")
        
        try:
            # Create all tables (only new ones will be created)
            db.create_all()
            
            print("✓ Database tables created/verified successfully!")
            
            print("\nNew tables added:")
            print("  - order_delivery: Stores delivery address and status for orders")
            print("    Fields: id, order_id, status, address, city, created_at, updated_at")
            print()
            print("  - vehicle_location: Stores city location for vehicles")
            print("    Fields: id, vehicle_id, city, created_at, updated_at")
            print()
            print("  - order_rating: Stores customer ratings for completed orders")
            print("    Fields: id, order_id, rating, comment, created_at, updated_at")
            print()
            print("  - vehicle_condition: Stores condition description for vehicles")
            print("    Fields: id, vehicle_id, description, created_at, updated_at")
            
            print("\n✅ Migration completed successfully!")
            print("\nNote: When you run the Flask app, these tables will be created automatically.")
            
        except Exception as e:
            print(f"\n❌ Error during migration: {str(e)}")
            raise

if __name__ == '__main__':
    migrate_database()

