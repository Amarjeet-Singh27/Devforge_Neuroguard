import os
from datetime import timedelta

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///neuroguard.db')
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # Upload Configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a', 'flac', 'webm'}
    
    # App Configuration
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    TESTING = False

    # OTP / Email Configuration
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', '10'))
    OTP_VERIFICATION_TOKEN_EXPIRY_MINUTES = int(os.environ.get('OTP_VERIFICATION_TOKEN_EXPIRY_MINUTES', '20'))

    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASS = os.environ.get('SMTP_PASS')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', SMTP_USER or 'no-reply@neuroguard.local')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', '1') == '1'
    ALLOW_OTP_FALLBACK = os.environ.get('ALLOW_OTP_FALLBACK', '1') == '1'

    # Lightweight middleware security controls
    JSON_MAX_BYTES = int(os.environ.get('JSON_MAX_BYTES', str(1024 * 1024)))  # 1MB
    FORM_MAX_BYTES = int(os.environ.get('FORM_MAX_BYTES', str(10 * 1024 * 1024)))  # 10MB
    RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', '60'))
    RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', '80'))

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///neuroguard.db')
    ALLOW_OTP_FALLBACK = False
    RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', '40'))

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    ALLOW_OTP_FALLBACK = True

config = {
    'development': Config,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config
}
