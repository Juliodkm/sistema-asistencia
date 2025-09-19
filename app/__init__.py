from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_login import LoginManager
from config import config # Import the config dictionary

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Por favor, inicia sesión para acceder a esta página.'
login.login_message_category = 'info'

def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    
    # Load configuration from the selected class
    app.config.from_object(config[config_name])

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login.init_app(app)

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.schedule import schedule_bp
    app.register_blueprint(schedule_bp, url_prefix='/admin/schedules')

    # Import models to ensure they are known to Flask-Migrate
    from app import models

    return app