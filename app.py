import os
import secrets
import time
from collections import defaultdict, deque
from flask import Flask, render_template, jsonify, request, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from models import db
from config import config
from routes.auth import auth_bp
from routes.voice import voice_bp
from routes.medicine import medicine_bp
from routes.contact import contact_bp

load_dotenv()

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])

    # Ensure JWT secret is always set; require env var for production.
    if not app.config.get('JWT_SECRET_KEY'):
        env_jwt_secret = os.environ.get('JWT_SECRET_KEY')
        if env_jwt_secret:
            app.config['JWT_SECRET_KEY'] = env_jwt_secret
        else:
            if config_name == 'production':
                raise RuntimeError("JWT_SECRET_KEY environment variable is required in production")
            # Stable fallback for local development so tokens remain valid across restarts.
            app.config['JWT_SECRET_KEY'] = 'dev-neuroguard-jwt-secret-32-bytes-min'
            print("[APP][WARNING] JWT_SECRET_KEY not set. Using development fallback secret.")
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    JWTManager(app)

    # Ensure runtime directories exist (important for hosted environments)
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Request guards are optional; keep disabled by default for legacy behavior.
    app.config.setdefault('ENABLE_REQUEST_GUARDS', False)
    app.config.setdefault('JSON_MAX_BYTES', 256 * 1024)  # 256KB
    app.config.setdefault('FORM_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
    app.config.setdefault('RATE_LIMIT_WINDOW_SECONDS', 60)
    app.config.setdefault('RATE_LIMIT_MAX_REQUESTS', 20)

    # In-memory rate-limit bucket for sensitive auth endpoints
    rate_buckets = defaultdict(deque)

    @app.before_request
    def request_security_guard():
        # Preserve pre-middleware behavior unless explicitly enabled.
        if not app.config.get('ENABLE_REQUEST_GUARDS', False):
            return None

        # Request size guard
        content_length = request.content_length or 0
        if request.path.startswith('/api'):
            if request.is_json and content_length > app.config['JSON_MAX_BYTES']:
                return jsonify({'error': 'Payload too large'}), 413
            if not request.is_json and content_length > app.config['FORM_MAX_BYTES']:
                return jsonify({'error': 'Payload too large'}), 413

        # Simple rate limiting on auth-sensitive endpoints
        sensitive_paths = {
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/request-otp',
            '/api/auth/verify-otp',
        }
        if request.path in sensitive_paths:
            now = time.time()
            window = app.config['RATE_LIMIT_WINDOW_SECONDS']
            max_requests = app.config['RATE_LIMIT_MAX_REQUESTS']
            client_key = f"{request.remote_addr}:{request.path}"
            bucket = rate_buckets[client_key]

            while bucket and (now - bucket[0]) > window:
                bucket.popleft()

            if len(bucket) >= max_requests:
                return jsonify({'error': 'Too many requests. Please try again later.'}), 429

            bucket.append(now)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(self), camera=()'
        # Keep CSP compatible with current inline scripts/styles used in templates.
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "media-src 'self' blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        return response
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(medicine_bp)
    app.register_blueprint(contact_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
        print("[APP] Database initialized")
    
    # Home route
    @app.route('/')
    def home():
        return render_template('index.html')
    
    # Dashboard route
    @app.route('/dashboard.html')
    def dashboard():
        return render_template('dashboard.html')
    
    # Voice test route
    @app.route('/voice-test.html')
    def voice_test():
        response = make_response(render_template('voice-test.html'))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response
    
    # Medicine check route
    @app.route('/medicine-check.html')
    def medicine_check():
        return render_template('medicine-check.html')
    
    # Results route
    @app.route('/result.html')
    def result():
        return render_template('result.html')

    # Contact route
    @app.route('/contact.html')
    def contact():
        return render_template('contact.html')

    # Admin messages route (hackathon demo)
    @app.route('/admin-messages.html')
    def admin_messages():
        return render_template('admin-messages.html')
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'NeuroGuard'}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({'error': 'Payload too large'}), 413
    
    print("[APP] NeuroGuard application started successfully!")
    return app

if __name__ == '__main__':
    app = create_app('development')
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5001'))
    use_https = os.environ.get('USE_HTTPS', '1').lower() not in ('0', 'false', 'no')

    if use_https:
        try:
            import cryptography  # noqa: F401
            print(f"[APP] Starting HTTPS dev server at https://{host}:{port}")
            print("[APP] Browser warning is expected for self-signed cert. Proceed to site, then allow microphone.")
            app.run(debug=app.config.get('DEBUG', False), host=host, port=port, ssl_context='adhoc')
        except ImportError:
            print("[APP][WARNING] 'cryptography' is not installed. Falling back to HTTP dev server.")
            print("[APP][TIP] Install it with: pip install cryptography")
            print(f"[APP] Starting HTTP dev server at http://{host}:{port}")
            app.run(debug=app.config.get('DEBUG', False), host=host, port=port)
    else:
        print(f"[APP] Starting HTTP dev server at http://{host}:{port}")
        app.run(debug=app.config.get('DEBUG', False), host=host, port=port)
