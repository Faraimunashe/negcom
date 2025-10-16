# Feature Update: Order Delivery, Vehicle Location, Order Rating, and Vehicle Condition

## Overview
This update adds four new models and their associated features to enhance the vehicle sales platform with delivery tracking, location information, order ratings, and vehicle condition details.

## New Models

### 1. OrderDelivery
**Purpose:** Track delivery information and status for each order.

**Fields:**
- `id` - Primary key
- `order_id` - Foreign key to Order (one-to-one relationship)
- `status` - Delivery status: 'pending', 'in_transit', 'delivered'
- `address` - Full delivery address (max 300 characters)
- `city` - City name (max 80 characters)
- `created_at` - Timestamp when created
- `updated_at` - Timestamp when last updated

**Relationship:** `Order.delivery` - Access delivery info from an order

### 2. VehicleLocation
**Purpose:** Store the location (city) where each vehicle is available.

**Fields:**
- `id` - Primary key
- `vehicle_id` - Foreign key to Vehicle (one-to-one relationship)
- `city` - City where vehicle is located (max 80 characters)
- `created_at` - Timestamp when created
- `updated_at` - Timestamp when last updated

**Relationship:** `Vehicle.location` - Access location info from a vehicle

### 3. OrderRating
**Purpose:** Allow customers to rate their order experience after delivery.

**Fields:**
- `id` - Primary key
- `order_id` - Foreign key to Order (one-to-one relationship)
- `rating` - Star rating (1-5 integer)
- `comment` - Optional text comment
- `created_at` - Timestamp when created
- `updated_at` - Timestamp when last updated

**Relationship:** `Order.rating` - Access rating info from an order

### 4. VehicleCondition
**Purpose:** Store the condition of each vehicle with predefined options.

**Fields:**
- `id` - Primary key
- `vehicle_id` - Foreign key to Vehicle (one-to-one relationship)
- `description` - Condition: 'new', 'used-excellent', 'used-good', 'used-fair', 'damaged'
- `created_at` - Timestamp when created
- `updated_at` - Timestamp when last updated

**Relationship:** `Vehicle.condition` - Access condition info from a vehicle

## New Forms

### 1. DeliveryAddressForm
Used during order creation to capture delivery information.

**Fields:**
- `address` - StringField (required, 10-300 characters)
- `city` - StringField (required, 2-80 characters)
- `submit` - SubmitField

### 2. OrderRatingForm
Used to rate completed orders.

**Fields:**
- `rating` - SelectField with star options (5-1 stars)
- `comment` - TextAreaField (optional, max 500 characters)
- `submit` - SubmitField

### 3. Updated AdminVehicleForm & AdminVehicleEditForm
Added fields for vehicle location and condition:
- `city` - StringField (required, 2-80 characters)
- `condition` - SelectField with options: New, Used-Excellent, Used-Good, Used-Fair, Damaged

## Updated Routes

### Orders Blueprint (`app/orders.py`)

#### Modified Routes:
- **`/orders/create/<vehicle_id>`** (GET, POST)
  - Now includes delivery address form
  - Creates OrderDelivery record along with Order
  - Redirects to payment page after successful creation

#### New Routes:
- **`/orders/<order_id>/rate`** (GET, POST)
  - Allows users to rate completed orders
  - Only accessible for paid orders
  - Prevents duplicate ratings
  - Updates delivery status to 'delivered' when rated

#### Updated Routes:
- **`/orders/<order_id>`** (GET)
  - Now fetches and displays delivery information
  - Shows rating if exists
  - Displays "Rate This Order" button for completed orders without ratings

### Admin Blueprint (`app/admin.py`)

#### Modified Routes:
- **`/admin/vehicles/create`** (GET, POST)
  - Creates VehicleLocation and VehicleCondition along with Vehicle
  - Requires city and condition fields

- **`/admin/vehicles/<vehicle_id>/edit`** (GET, POST)
  - Updates or creates VehicleLocation and VehicleCondition
  - Pre-fills form with existing location and condition data

- **`/admin/vehicles/<vehicle_id>`** (GET)
  - Fetches and displays location and condition information

### Vehicles Blueprint (`app/vehicles.py`)

#### Modified Routes:
- **`/vehicles/<vehicle_id>`** (GET)
  - Fetches and displays vehicle location and condition
  - Shows location and condition to potential buyers

## New Templates

### 1. `app/templates/orders/create_order.html`
**Purpose:** Display delivery address form during order creation

**Features:**
- Clean form layout with address and city fields
- Vehicle summary sidebar showing order details
- Responsive design with Tailwind CSS

### 2. `app/templates/orders/rate.html`
**Purpose:** Allow users to rate completed orders

**Features:**
- Star rating selector (5-1 stars with emojis)
- Optional comment text area
- Order and vehicle summary sidebar
- Information box explaining rating importance

### 3. Updated `app/templates/orders/detail.html`
**Features Added:**
- Delivery Information section showing address, city, and status
- Your Rating section showing submitted rating and comment
- "Rate This Order" button for completed orders without ratings

## Database Migration

The new tables will be created automatically when you run the Flask app, as `db.create_all()` is called in `app/__init__.py`.

Alternatively, you can run the migration script manually:

```bash
python migrate_db.py
```

## Usage Flow

### For Buyers:

1. **Browse Vehicles**
   - View vehicle location and condition on detail page
   
2. **Create Order**
   - Click "Buy Now" on vehicle detail page
   - Fill in delivery address and city
   - Proceed to payment

3. **Complete Order**
   - Make payment
   - View order details with delivery information
   
4. **Rate Order**
   - After receiving vehicle, click "Rate This Order"
   - Select star rating and optionally add comment
   - Submit rating

### For Admins:

1. **Create Vehicle**
   - Fill in all vehicle details
   - **New:** Select city location
   - **New:** Select vehicle condition
   - Upload images
   - Submit

2. **Edit Vehicle**
   - Update vehicle details
   - **New:** Update location city
   - **New:** Update condition description
   - Save changes

3. **View Orders**
   - See delivery information for each order
   - Monitor delivery status
   - View customer ratings

## API Changes

### Order Model Relationships
```python
# Access delivery info
order = Order.query.get(order_id)
delivery = order.delivery  # Returns OrderDelivery object or None

# Access rating
rating = order.rating  # Returns OrderRating object or None
```

### Vehicle Model Relationships
```python
# Access location
vehicle = Vehicle.query.get(vehicle_id)
location = vehicle.location  # Returns VehicleLocation object or None

# Access condition
condition = vehicle.condition  # Returns VehicleCondition object or None
```

## Files Modified

### Backend:
- `app/models.py` - Added 4 new models
- `app/forms.py` - Added 2 new forms, updated 2 admin forms
- `app/orders.py` - Updated order creation, added rating route
- `app/admin.py` - Updated vehicle creation/editing
- `app/vehicles.py` - Added location and condition to detail view

### Templates:
- `app/templates/orders/detail.html` - Added delivery and rating sections
- `app/templates/orders/create_order.html` - **New** - Delivery address form
- `app/templates/orders/rate.html` - **New** - Rating form

### New Files:
- `migrate_db.py` - Database migration script
- `FEATURE_UPDATE.md` - This documentation

## Testing Checklist

- [ ] Create a new vehicle with location and condition
- [ ] Edit existing vehicle to add location and condition
- [ ] Create an order and provide delivery address
- [ ] Complete payment for an order
- [ ] Rate a completed order
- [ ] View order details with delivery information
- [ ] Verify vehicle details show location and condition
- [ ] Test that you cannot rate an order twice
- [ ] Test that rating button only shows for paid orders

## Notes

- Delivery status starts as 'pending' when order is created
- Delivery status changes to 'delivered' when order is rated
- Ratings are on a scale of 1-5 stars
- Vehicle conditions are predefined choices for consistency
- All new fields include proper validation
- Foreign key relationships ensure data integrity

## Future Enhancements

Potential improvements to consider:
- Add delivery tracking with multiple status updates
- Include postal/zip code in delivery address
- Add delivery date estimation
- Allow admins to update delivery status
- Show vehicle location on a map
- Add filtering by location/condition in browse page
- Display average ratings on vehicle listings
- Add photos to ratings
- Send email notifications for delivery updates

