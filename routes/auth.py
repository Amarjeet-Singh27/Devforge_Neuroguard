from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User
from datetime import datetime, timedelta
import secrets
import smtplib
from email.mime.text import MIMEText

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
OTP_STORE = {}
VERIFIED_SIGNUP_STORE = {}


def _otp_expiry_delta():
    minutes = int(current_app.config.get('OTP_EXPIRY_MINUTES', 10))
    return timedelta(minutes=minutes)


def _verification_expiry_delta():
    minutes = int(current_app.config.get('OTP_VERIFICATION_TOKEN_EXPIRY_MINUTES', 20))
    return timedelta(minutes=minutes)


def _send_email(recipient_email, subject, body):
    smtp_host = current_app.config.get('SMTP_HOST')
    smtp_port = current_app.config.get('SMTP_PORT')
    smtp_user = current_app.config.get('SMTP_USER')
    smtp_pass = current_app.config.get('SMTP_PASS')
    from_email = current_app.config.get('SMTP_FROM_EMAIL')
    use_tls = current_app.config.get('SMTP_USE_TLS', True)

    if not smtp_host or not smtp_user or not smtp_pass:
        return False, 'SMTP is not configured'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [recipient_email], msg.as_string())
        return True, None
    except Exception as exc:
        return False, str(exc)


def _send_signup_otp_email(recipient_email, otp_code):
    subject = 'NeuroGuard Signup OTP'
    body = (
        f"Your NeuroGuard OTP is: {otp_code}\n\n"
        "This OTP is valid for 10 minutes.\n"
        "If you did not request this, please ignore this email."
    )
    return _send_email(recipient_email, subject, body)


def _cleanup_auth_temp_store():
    now = datetime.utcnow()
    for email, record in list(OTP_STORE.items()):
        if record['expires_at'] < now:
            del OTP_STORE[email]
    for token, record in list(VERIFIED_SIGNUP_STORE.items()):
        if record['expires_at'] < now:
            del VERIFIED_SIGNUP_STORE[token]


@auth_bp.route('/otp-status', methods=['GET'])
def otp_status():
    """Return current OTP delivery mode status for signup UI."""
    smtp_ready = bool(
        current_app.config.get('SMTP_HOST')
        and current_app.config.get('SMTP_USER')
        and current_app.config.get('SMTP_PASS')
    )
    fallback_enabled = bool(current_app.config.get('ALLOW_OTP_FALLBACK', False))
    delivery_mode = 'smtp' if smtp_ready else ('fallback' if fallback_enabled else 'unavailable')

    return jsonify({
        'smtp_configured': smtp_ready,
        'fallback_enabled': fallback_enabled,
        'delivery_mode': delivery_mode
    }), 200


@auth_bp.route('/request-otp', methods=['POST'])
def request_signup_otp():
    """
    Request an OTP for signup email verification
    Required: email
    """
    try:
        _cleanup_auth_temp_store()
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        otp_code = f"{secrets.randbelow(1000000):06d}"
        expiry_delta = _otp_expiry_delta()
        OTP_STORE[email] = {
            'otp': otp_code,
            'expires_at': datetime.utcnow() + expiry_delta
        }

        sent, send_error = _send_signup_otp_email(email, otp_code)
        expires_in_seconds = int(expiry_delta.total_seconds())

        if sent:
            return jsonify({
                'message': 'OTP sent to your email',
                'expires_in_seconds': expires_in_seconds,
                'email_delivery': 'smtp'
            }), 200

        print(f"[AUTH][OTP] Email send failed for {email}: {send_error}")
        allow_fallback = bool(current_app.config.get('ALLOW_OTP_FALLBACK', False))
        if allow_fallback:
            return jsonify({
                'message': 'SMTP unavailable. Using demo OTP fallback.',
                'expires_in_seconds': expires_in_seconds,
                'email_delivery': 'fallback',
                'demo_otp': otp_code
            }), 200

        return jsonify({
            'error': 'OTP email could not be sent. Please contact admin to configure SMTP and try again.'
        }), 503
    except Exception as e:
        print(f"[AUTH][request_otp] Error: {str(e)}")
        return jsonify({'error': 'Failed to send OTP'}), 500


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_signup_otp():
    """
    Verify signup OTP and return a one-time verification token
    Required: email, otp
    """
    try:
        _cleanup_auth_temp_store()
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        otp = (data.get('otp') or '').strip()

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        otp_record = OTP_STORE.get(email)
        if not otp_record:
            return jsonify({'error': 'OTP not found. Request a new OTP'}), 404

        if otp_record['expires_at'] < datetime.utcnow():
            del OTP_STORE[email]
            return jsonify({'error': 'OTP expired. Request a new OTP'}), 400

        if otp_record['otp'] != otp:
            return jsonify({'error': 'Invalid OTP'}), 400

        del OTP_STORE[email]
        verification_token = secrets.token_urlsafe(24)
        verification_expiry_delta = _verification_expiry_delta()
        VERIFIED_SIGNUP_STORE[verification_token] = {
            'email': email,
            'expires_at': datetime.utcnow() + verification_expiry_delta
        }

        return jsonify({
            'message': 'Email verified successfully',
            'verification_token': verification_token
        }), 200
    except Exception as e:
        print(f"[AUTH][verify_otp] Error: {str(e)}")
        return jsonify({'error': 'Failed to verify OTP'}), 500


@auth_bp.route('/test-smtp', methods=['POST'])
def test_smtp():
    """
    Send a test email to verify SMTP settings.
    Enabled only in DEBUG or TESTING mode.
    Body: { "email": "recipient@example.com" }
    """
    try:
        if not (current_app.config.get('DEBUG') or current_app.config.get('TESTING')):
            return jsonify({'error': 'SMTP test endpoint is disabled in production'}), 403

        data = request.get_json() or {}
        recipient_email = (data.get('email') or '').strip()
        if not recipient_email:
            recipient_email = (
                current_app.config.get('SMTP_FROM_EMAIL')
                or current_app.config.get('SMTP_USER')
                or ''
            ).strip()

        if not recipient_email:
            return jsonify({'error': 'Provide an email in request body'}), 400

        sent, send_error = _send_email(
            recipient_email,
            'NeuroGuard SMTP Test',
            'This is a test email from NeuroGuard SMTP configuration.'
        )

        if not sent:
            return jsonify({'error': f'SMTP test failed: {send_error}'}), 503

        return jsonify({'message': f'SMTP test email sent to {recipient_email}'}), 200
    except Exception as e:
        print(f"[AUTH][test_smtp] Error: {str(e)}")
        return jsonify({'error': 'SMTP test failed'}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    Required: email, password, full_name, user_type (patient/admin)
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        required = ['email', 'password', 'full_name', 'user_type']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        email = data['email'].strip().lower()
        user_type = (data.get('user_type') or '').strip().lower()

        if user_type not in {'patient', 'admin'}:
            return jsonify({'error': "Invalid user_type. Allowed values: 'patient', 'admin'"}), 400

        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Optional OTP verification token flow (used by UI signup wizard)
        verification_token = data.get('verification_token')
        if verification_token:
            _cleanup_auth_temp_store()
            verification_record = VERIFIED_SIGNUP_STORE.get(verification_token)
            if not verification_record:
                return jsonify({'error': 'Invalid or expired verification token'}), 400
            if verification_record['email'] != email:
                return jsonify({'error': 'Verification token does not match email'}), 400
            del VERIFIED_SIGNUP_STORE[verification_token]

        # Create new user
        user = User(
            email=email,
            full_name=data['full_name'],
            user_type=user_type,
            age=data.get('age')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH][register] Error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user and return JWT token
    Required: email, password
    """
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 200
        
    except Exception as e:
        print(f"[AUTH][login] Error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        print(f"[AUTH][profile] Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch profile'}), 500

@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'age' in data:
            user.age = data['age']
        if 'medical_history' in data:
            user.medical_history = data['medical_history']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH][update_profile] Error: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500
