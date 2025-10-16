from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, SelectField, DateField, DateTimeField, TimeField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Regexp, Optional, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField
from datetime import datetime, date, time, timedelta
from flask_wtf.file import FileField, FileAllowed, FileRequired, MultipleFileField


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()], 
                       render_kw={"placeholder": "Enter your email", "autofocus": True, 
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)], 
                           render_kw={"placeholder": "Enter your password", 
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Sign In', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})
   

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=50)], 
                      render_kw={"placeholder": "Enter your full name", "autofocus": True,
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    email = StringField('Email', validators=[DataRequired(), Email()], 
                       render_kw={"placeholder": "Enter your email",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)], 
                           render_kw={"placeholder": "Create a password",
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')], 
                                   render_kw={"placeholder": "Confirm your password",
                                             "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Create Account', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})


# Vehicle-related forms
class VehicleSearchForm(FlaskForm):
    search = StringField('Search', validators=[Optional()], 
                        render_kw={"placeholder": "Search by make, model, or description",
                                  "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Search', render_kw={"class": "bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition duration-200"})

class VehicleFilterForm(FlaskForm):
    category = SelectField('Category', coerce=int, validators=[Optional()],
                          render_kw={"class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    min_price = DecimalField('Min Price', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Min price", "step": "0.01",
                                      "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    max_price = DecimalField('Max Price', validators=[Optional(), NumberRange(min=0)],
                            render_kw={"placeholder": "Max price", "step": "0.01",
                                      "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    min_year = IntegerField('Min Year', validators=[Optional(), NumberRange(min=1900, max=2030)],
                           render_kw={"placeholder": "Min year",
                                     "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    max_year = IntegerField('Max Year', validators=[Optional(), NumberRange(min=1900, max=2030)],
                           render_kw={"placeholder": "Max year",
                                     "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    min_mileage = IntegerField('Min Mileage', validators=[Optional(), NumberRange(min=0)],
                              render_kw={"placeholder": "Min mileage",
                                        "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    max_mileage = IntegerField('Max Mileage', validators=[Optional(), NumberRange(min=0)],
                              render_kw={"placeholder": "Max mileage",
                                        "class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    fuel_type = SelectField('Fuel Type', choices=[
        ('', 'All Fuel Types'),
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('lpg', 'LPG'),
        ('cng', 'CNG')
    ], validators=[Optional()],
    render_kw={"class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    transmission = SelectField('Transmission', choices=[
        ('', 'All Transmissions'),
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('semi-automatic', 'Semi-Automatic'),
        ('cvt', 'CVT')
    ], validators=[Optional()],
    render_kw={"class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    sort_by = SelectField('Sort By', choices=[
        ('created_at', 'Newest First'),
        ('price_asc', 'Price: Low to High'),
        ('price_desc', 'Price: High to Low'),
        ('year_desc', 'Year: Newest First'),
        ('year_asc', 'Year: Oldest First'),
        ('mileage_asc', 'Mileage: Low to High'),
        ('mileage_desc', 'Mileage: High to Low')
    ], default='created_at',
    render_kw={"class": "w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Apply Filters', render_kw={"class": "w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition duration-200"})

class NegotiationForm(FlaskForm):
    offer_amount = DecimalField('Your Offer', validators=[DataRequired(), NumberRange(min=0.01)],
                               render_kw={"placeholder": "Enter your offer amount", "step": "0.01",
                                         "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    message = TextAreaField('Message', validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Add a message to your offer (optional)",
                                     "rows": 4,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Send Offer', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class ContactSellerForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=100)],
                         render_kw={"placeholder": "Message subject",
                                   "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=1000)],
                           render_kw={"placeholder": "Your message to the seller",
                                     "rows": 5,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Send Message', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})

# Negotiation-related forms
class NegotiationForm(FlaskForm):
    offer_amount = DecimalField('Your Offer', validators=[DataRequired(), NumberRange(min=0.01)],
                               render_kw={"placeholder": "Enter your offer amount", "step": "0.01",
                                         "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    message = TextAreaField('Message', validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Add a message to your offer (optional)",
                                     "rows": 4,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Send Offer', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class CounterOfferForm(FlaskForm):
    counter_amount = DecimalField('Counter Offer', validators=[DataRequired(), NumberRange(min=0.01)],
                                 render_kw={"placeholder": "Enter your counter offer", "step": "0.01",
                                           "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    message = TextAreaField('Message', validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Add a message to your counter offer (optional)",
                                     "rows": 4,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Send Counter Offer', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})

class NegotiationMessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=5, max=1000)],
                           render_kw={"placeholder": "Type your message here...",
                                     "rows": 4,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Send Message', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

# Order and Payment Forms
class PaymentForm(FlaskForm):
    payment_method = SelectField('Payment Method', 
                                choices=[
                                    ('credit_card', 'Credit Card'),
                                    ('paypal', 'PayPal'),
                                    ('bank_transfer', 'Bank Transfer'),
                                    ('mobile_money', 'Mobile Money')
                                ],
                                validators=[DataRequired()],
                                render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    card_number = StringField('Card Number', 
                             validators=[Optional(), Length(min=13, max=19)],
                             render_kw={"placeholder": "1234 5678 9012 3456",
                                       "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    expiry_date = StringField('Expiry Date', 
                             validators=[Optional(), Length(min=5, max=5)],
                             render_kw={"placeholder": "MM/YY",
                                       "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    cvv = StringField('CVV', 
                     validators=[Optional(), Length(min=3, max=4)],
                     render_kw={"placeholder": "123",
                               "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    account_number = StringField('Account Number', 
                                validators=[Optional(), Length(min=8, max=20)],
                                render_kw={"placeholder": "Enter your account number",
                                          "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    mobile_number = StringField('Mobile Number', 
                               validators=[Optional(), Length(min=10, max=15)],
                               render_kw={"placeholder": "Enter your mobile number",
                                         "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    
    submit = SubmitField('Process Payment', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})

# Admin Forms
class AdminVehicleForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "e.g., Toyota, Honda, BMW",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    model = StringField('Model', validators=[DataRequired(), Length(min=2, max=80)],
                       render_kw={"placeholder": "e.g., Camry, Civic, 3 Series",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2030)],
                       render_kw={"placeholder": "e.g., 2020",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    mileage = IntegerField('Mileage (km)', validators=[DataRequired(), NumberRange(min=0)],
                          render_kw={"placeholder": "e.g., 35000",
                                    "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    engine_type = SelectField('Engine Type', choices=[
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('lpg', 'LPG'),
        ('cng', 'CNG')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    transmission = SelectField('Transmission', choices=[
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('semi-automatic', 'Semi-Automatic'),
        ('cvt', 'CVT')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    body_type = SelectField('Body Type', choices=[
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Hatchback', 'Hatchback'),
        ('Coupe', 'Coupe'),
        ('Convertible', 'Convertible'),
        ('Truck', 'Truck'),
        ('Van', 'Van'),
        ('Wagon', 'Wagon')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    color = StringField('Color', validators=[DataRequired(), Length(min=2, max=80)],
                       render_kw={"placeholder": "e.g., Silver, Black, White",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    price = DecimalField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)],
                        render_kw={"placeholder": "e.g., 25000.00", "step": "0.01",
                                  "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    city = StringField('Location (City)', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "e.g., Harare, Bulawayo",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    condition = SelectField('Condition', choices=[
        ('new', 'New'),
        ('used-excellent', 'Used - Excellent'),
        ('used-good', 'Used - Good'),
        ('used-fair', 'Used - Fair'),
        ('damaged', 'Damaged')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    images = MultipleFileField('Vehicle Images', validators=[
        FileRequired(message='At least one image is required'),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only image files (JPG, PNG, GIF) are allowed!')
    ], render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent", "multiple": True, "accept": "image/*"})
    submit = SubmitField('Save Vehicle', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class AdminVehicleEditForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "e.g., Toyota, Honda, BMW",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    model = StringField('Model', validators=[DataRequired(), Length(min=2, max=80)],
                       render_kw={"placeholder": "e.g., Camry, Civic, 3 Series",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2030)],
                       render_kw={"placeholder": "e.g., 2020",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    mileage = IntegerField('Mileage (km)', validators=[DataRequired(), NumberRange(min=0)],
                          render_kw={"placeholder": "e.g., 35000",
                                    "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    engine_type = SelectField('Engine Type', choices=[
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('lpg', 'LPG'),
        ('cng', 'CNG')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    transmission = SelectField('Transmission', choices=[
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('semi-automatic', 'Semi-Automatic'),
        ('cvt', 'CVT')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    body_type = SelectField('Body Type', choices=[
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV'),
        ('Hatchback', 'Hatchback'),
        ('Coupe', 'Coupe'),
        ('Convertible', 'Convertible'),
        ('Truck', 'Truck'),
        ('Van', 'Van'),
        ('Wagon', 'Wagon')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    color = StringField('Color', validators=[DataRequired(), Length(min=2, max=80)],
                       render_kw={"placeholder": "e.g., Silver, Black, White",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    price = DecimalField('Price ($)', validators=[DataRequired(), NumberRange(min=0.01)],
                        render_kw={"placeholder": "e.g., 25000.00", "step": "0.01",
                                  "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    city = StringField('Location (City)', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "e.g., Harare, Bulawayo",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    condition = SelectField('Condition', choices=[
        ('new', 'New'),
        ('used-excellent', 'Used - Excellent'),
        ('used-good', 'Used - Good'),
        ('used-fair', 'Used - Fair'),
        ('damaged', 'Damaged')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    additional_images = MultipleFileField('Additional Images (Optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only image files (JPG, PNG, GIF) are allowed!')
    ], render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent", "multiple": True, "accept": "image/*"})
    submit = SubmitField('Update Vehicle', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class AdminUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "Enter full name",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    email = StringField('Email', validators=[DataRequired(), Email()],
                       render_kw={"placeholder": "Enter email address",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    role = SelectField('Role', choices=[
        (1, 'Admin'),
        (2, 'User')
    ], coerce=int, validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Update User', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})

class AdminUserCreateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "Enter full name",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    email = StringField('Email', validators=[DataRequired(), Email()],
                       render_kw={"placeholder": "Enter email address",
                                 "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)],
                            render_kw={"placeholder": "Enter password",
                                      "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')],
                                    render_kw={"placeholder": "Confirm password",
                                              "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    role = SelectField('Role', choices=[
        (1, 'Admin'),
        (2, 'User')
    ], coerce=int, validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Create User', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class AdminOrderForm(FlaskForm):
    status = SelectField('Order Status', choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Update Order', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})

class AdminNegotiationForm(FlaskForm):
    status = SelectField('Negotiation Status', choices=[
        ('ongoing', 'Ongoing'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    final_price = DecimalField('Final Price ($)', validators=[Optional(), NumberRange(min=0.01)],
                              render_kw={"placeholder": "e.g., 22000.00", "step": "0.01",
                                        "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Update Negotiation', render_kw={"class": "w-full bg-purple-600 text-white py-3 px-4 rounded-lg hover:bg-purple-700 transition duration-200 font-medium"})

class AdminDiscountRuleForm(FlaskForm):
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[DataRequired()],
                            render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    max_discount_percentage = DecimalField('Max Discount (%)', validators=[DataRequired(), NumberRange(min=0.01, max=99.99)],
                                          render_kw={"placeholder": "e.g., 15.00", "step": "0.01",
                                                    "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    min_price_allowed = DecimalField('Min Price Allowed ($)', validators=[DataRequired(), NumberRange(min=0.01)],
                                    render_kw={"placeholder": "e.g., 18000.00", "step": "0.01",
                                              "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Save Discount Rule', render_kw={"class": "w-full bg-yellow-600 text-white py-3 px-4 rounded-lg hover:bg-yellow-700 transition duration-200 font-medium"})

class AdminReportForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()],
                          render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    end_date = DateField('End Date', validators=[DataRequired()],
                        render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    report_type = SelectField('Report Type', choices=[
        ('sales', 'Sales Report'),
        ('users', 'User Report'),
        ('vehicles', 'Vehicle Report'),
        ('negotiations', 'Negotiation Report')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Generate Report', render_kw={"class": "w-full bg-indigo-600 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 transition duration-200 font-medium"})

# Delivery and Rating Forms
class DeliveryAddressForm(FlaskForm):
    address = StringField('Delivery Address', validators=[DataRequired(), Length(min=10, max=300)],
                         render_kw={"placeholder": "Enter full street address",
                                   "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=80)],
                      render_kw={"placeholder": "Enter city",
                                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Proceed to Payment', render_kw={"class": "w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition duration-200 font-medium"})

class OrderRatingForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '⭐⭐⭐⭐⭐ Excellent'),
        ('4', '⭐⭐⭐⭐ Good'),
        ('3', '⭐⭐⭐ Average'),
        ('2', '⭐⭐ Poor'),
        ('1', '⭐ Very Poor')
    ], validators=[DataRequired()],
    render_kw={"class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    comment = TextAreaField('Comment (Optional)', validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Share your experience with this order...",
                                     "rows": 4,
                                     "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"})
    submit = SubmitField('Submit Rating', render_kw={"class": "w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition duration-200 font-medium"})