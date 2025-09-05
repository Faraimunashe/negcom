from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, SelectField, DateField, DateTimeField, TimeField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Regexp, Optional, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField
from datetime import datetime, date, time, timedelta
from flask_wtf.file import FileField, FileAllowed, FileRequired


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
