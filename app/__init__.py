from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'ProfessorSecret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vehicle_sales.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'faraimunashe.m11@gmail.com'
    app.config['MAIL_PASSWORD'] = 'vdpdwbzmbhflivoc'
    app.config['MAIL_DEFAULT_SENDER'] = 'faraimunashe.m11@gmail.com'


    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .vehicles import vehicles_bp
    from .negotiations import negotiations_bp
    from .orders import orders_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(negotiations_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app
