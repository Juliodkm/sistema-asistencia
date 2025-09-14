from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Por favor, inicia sesión para acceder a esta página.'
login.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app import models

    return app
