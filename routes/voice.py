from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import json
import shutil
from datetime import datetime
import uuid
from models import db, VoiceTest, User
from utils.voice_analyzer import VoiceAnalyzer
from utils.pdf_report import build_voice_report_pdf
from config import Config

voice_bp = Blueprint('voice', __name__, url_prefix='/api/voice')
analyzer = VoiceAnalyzer()


def _resolve_upload_filename(upload_file):
    """Build a safe filename even when browser-provided names are missing/invalid."""
    original_name = (upload_file.filename or '').strip()
    safe_name = secure_filename(original_name)

    ext = os.path.splitext(original_name)[1].lower()
    if not ext:
        mimetype_to_ext = {
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/ogg': '.ogg',
            'audio/webm': '.webm',
            'audio/mp4': '.m4a',
            'audio/x-m4a': '.m4a',
            'audio/flac': '.flac',
            'audio/x-flac': '.flac',
        }
        ext = mimetype_to_ext.get((upload_file.mimetype or '').lower(), '')

    if not safe_name:
        unique = uuid.uuid4().hex[:10]
        safe_name = f"voice_{unique}{ext or '.wav'}"

    return safe_name

@voice_bp.route('/test', methods=['POST'])
@jwt_required()
def voice_test():
    """
    Upload and analyze voice audio
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if file is present
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Resolve a safe filename first (mobile uploads may send blank/unsafe names)
        filename = _resolve_upload_filename(file)

        # Validate file extension
        if not allowed_file(filename):
            return jsonify({'error': 'Invalid file format. Allowed: wav, mp3, ogg, m4a, flac, webm'}), 400
        
        # Create uploads folder if not exists
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        
        # Save file (avoid clobbering an existing file with same name)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        print(f"[VOICE] Testing audio: {filepath}")
        
        # Analyze voice
        analysis = analyzer.analyze(filepath)
        
        if 'error' in analysis:
            return jsonify({'error': 'Analysis failed: ' + analysis['error']}), 500
        
        detected_level = analysis.get('stress_level') or analysis.get('risk_level') or 'Unknown'
        detected_score = analysis.get('stress_score', analysis.get('risk_score', 0))

        reference_sentence = (request.form.get('reference_sentence') or '').strip()
        source = (request.form.get('source') or '').strip()

        # Save test result to database
        voice_test = VoiceTest(
            patient_id=user_id,
            audio_filename=filename,
            audio_path=filepath,
            risk_level=detected_level,
            risk_score=detected_score,
            slurring_score=analysis['slurring_score'],
            speech_delay_score=analysis['speech_delay_score'],
            frequency_variation_score=analysis['frequency_variation_score'],
            tremor_score=analysis['tremor_score'],
            recommendations=analysis['recommendations'],
            test_date=datetime.utcnow()
        )
        
        db.session.add(voice_test)
        db.session.commit()
        
        return jsonify({
            'message': 'Voice test completed',
            'test_result': {
                **voice_test.to_dict(),
                'reference_sentence': reference_sentence or None,
                'source': source or None,
                'model_confidence': analysis.get('model_confidence'),
                'model_probabilities': analysis.get('model_probabilities', {})
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[VOICE] Error: {str(e)}")
        return jsonify({'error': f'Voice analysis failed: {str(e)}'}), 500

@voice_bp.route('/history', methods=['GET'])
@jwt_required()
def voice_history():
    """
    Get all voice tests for current user
    """
    try:
        user_id = get_jwt_identity()
        
        tests = VoiceTest.query.filter_by(patient_id=user_id).order_by(VoiceTest.test_date.desc()).all()
        
        return jsonify({
            'total_tests': len(tests),
            'tests': [test.to_dict() for test in tests]
        }), 200
        
    except Exception as e:
        print(f"[VOICE][history] Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch voice history'}), 500

@voice_bp.route('/test/<test_id>', methods=['GET'])
@jwt_required()
def get_test(test_id):
    """
    Get specific voice test result
    """
    try:
        user_id = get_jwt_identity()
        
        test = VoiceTest.query.filter_by(id=test_id, patient_id=user_id).first()
        
        if not test:
            return jsonify({'error': 'Test not found'}), 404
        
        return jsonify(test.to_dict()), 200
        
    except Exception as e:
        print(f"[VOICE][get_test] Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch test result'}), 500


@voice_bp.route('/test/<test_id>/report.pdf', methods=['GET'])
@jwt_required()
def download_test_report(test_id):
    """
    Download a printable PDF report for a specific voice test
    """
    try:
        user_id = get_jwt_identity()
        test = VoiceTest.query.filter_by(id=test_id, patient_id=user_id).first()

        if not test:
            return jsonify({'error': 'Test not found'}), 404

        payload = test.to_dict()
        payload['audio_path'] = os.path.abspath(test.audio_path) if test.audio_path else None
        payload['audio_filename'] = test.audio_filename
        pdf_bytes = build_voice_report_pdf(payload)
        filename = f"voice_report_{str(test.id)[:8]}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Cache-Control': 'no-store'
            }
        )

    except Exception as e:
        print(f"[VOICE][download_report] Error: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF report'}), 500

@voice_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """
    Get voice test statistics
    """
    try:
        user_id = get_jwt_identity()
        
        tests = VoiceTest.query.filter_by(patient_id=user_id).order_by(VoiceTest.test_date.desc()).all()
        
        if not tests:
            return jsonify({
                'total_tests': 0,
                'average_risk_score': 0,
                'average_stress_score': 0,
                'risk_distribution': {},
                'stress_distribution': {}
            }), 200
        
        risk_counts = {'Low': 0, 'Medium': 0, 'High': 0}
        total_score = 0
        
        for test in tests:
            risk_counts[test.risk_level] = risk_counts.get(test.risk_level, 0) + 1
            total_score += test.risk_score
        
        return jsonify({
            'total_tests': len(tests),
            'average_risk_score': round(total_score / len(tests), 2),
            'average_stress_score': round(total_score / len(tests), 2),
            'risk_distribution': risk_counts,
            'stress_distribution': risk_counts,
            'latest_test': tests[0].to_dict() if tests else None
        }), 200
        
    except Exception as e:
        print(f"[VOICE][stats] Error: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500


@voice_bp.route('/model-metrics', methods=['GET'])
@jwt_required()
def get_model_metrics():
    """Return model evaluation metrics generated by evaluate_model.py"""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        metrics_path = os.path.join(project_root, 'model_metrics.json')

        if not os.path.exists(metrics_path):
            return jsonify({
                'error': 'model_metrics.json not found',
                'hint': 'Run evaluate_model.py after training the model'
            }), 404

        with open(metrics_path, 'r', encoding='utf-8') as metrics_file:
            metrics = json.load(metrics_file)

        return jsonify(metrics), 200

    except Exception as e:
        print(f"[VOICE][model_metrics] Error: {str(e)}")
        return jsonify({'error': 'Failed to load model metrics'}), 500


@voice_bp.route('/dataset/unlabeled', methods=['GET'])
@jwt_required()
def get_unlabeled_files():
    """List unlabeled audio files waiting for manual dataset labeling."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        unlabeled_dir = os.path.join(project_root, 'dataset', 'unlabeled')

        if not os.path.exists(unlabeled_dir):
            return jsonify({
                'total_unlabeled': 0,
                'files': []
            }), 200

        files = []
        for file_name in os.listdir(unlabeled_dir):
            full_path = os.path.join(unlabeled_dir, file_name)
            if os.path.isfile(full_path):
                files.append(file_name)

        files.sort()
        return jsonify({
            'total_unlabeled': len(files),
            'files': files
        }), 200

    except Exception as e:
        print(f"[VOICE][unlabeled] Error: {str(e)}")
        return jsonify({'error': 'Failed to list unlabeled files'}), 500


@voice_bp.route('/dataset/label', methods=['POST'])
@jwt_required()
def label_dataset_file():
    """Move one file from dataset/unlabeled to dataset/{low|medium|high}."""
    try:
        data = request.get_json() or {}
        file_name = data.get('file_name', '').strip()
        label = data.get('label', '').strip().lower()

        if not file_name or not label:
            return jsonify({'error': 'file_name and label are required'}), 400

        valid_labels = {'low', 'medium', 'high'}
        if label not in valid_labels:
            return jsonify({'error': 'label must be one of: low, medium, high'}), 400

        safe_name = os.path.basename(file_name)
        if safe_name != file_name:
            return jsonify({'error': 'Invalid file_name'}), 400

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        src_dir = os.path.join(project_root, 'dataset', 'unlabeled')
        dst_dir = os.path.join(project_root, 'dataset', label)

        src_path = os.path.join(src_dir, safe_name)
        if not os.path.exists(src_path):
            return jsonify({'error': 'File not found in dataset/unlabeled'}), 404

        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)

        dst_path = os.path.join(dst_dir, safe_name)
        if os.path.exists(dst_path):
            base, ext = os.path.splitext(safe_name)
            counter = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(dst_dir, f"{base}_{counter}{ext}")
                counter += 1

        shutil.move(src_path, dst_path)

        return jsonify({
            'message': 'File labeled successfully',
            'file_name': os.path.basename(dst_path),
            'label': label,
            'destination': dst_path
        }), 200

    except Exception as e:
        print(f"[VOICE][label] Error: {str(e)}")
        return jsonify({'error': 'Failed to label dataset file'}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
