import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class. Contains shared configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Add other shared configurations here

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'postgresql://admin:password123@localhost/asistencia_db'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # For production, these MUST be set in the environment
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') # Render sets this automatically

# Dictionary to map configuration names to their respective classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}