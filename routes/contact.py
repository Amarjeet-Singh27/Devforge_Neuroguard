from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import db, ContactMessage, User


contact_bp = Blueprint('contact', __name__, url_prefix='/api/contact')


@contact_bp.route('', methods=['POST'])
def submit_contact_message():
    """
    Save contact form message to database
    Required: name, email, subject, message
    """
    try:
        data = request.get_json() or {}

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        subject = (data.get('subject') or '').strip()
        message = (data.get('message') or '').strip()

        if not name or not email or not subject or not message:
            return jsonify({'error': 'name, email, subject and message are required'}), 400

        entry = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )
        db.session.add(entry)
        db.session.commit()

        return jsonify({
            'message': 'Contact message saved successfully',
            'contact': entry.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"[CONTACT][submit] Error: {str(e)}")
        return jsonify({'error': 'Failed to save contact message'}), 500


@contact_bp.route('/list', methods=['GET'])
@jwt_required()
def list_contact_messages():
    """
    List contact messages for authenticated users (hackathon demo/admin endpoint).
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if (user.user_type or '').lower() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
        return jsonify({
            'total_messages': len(messages),
            'messages': [item.to_dict() for item in messages]
        }), 200
    except Exception as e:
        print(f"[CONTACT][list] Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch contact messages'}), 500
