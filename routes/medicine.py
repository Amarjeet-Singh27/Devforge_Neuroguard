from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Medicine, SupplyChainRecord, Prescription, User
from utils.hash_chain import MedicineHashChain
from datetime import datetime
import json
import ast

medicine_bp = Blueprint('medicine', __name__, url_prefix='/api/medicine')

@medicine_bp.route('/register-batch', methods=['POST'])
@jwt_required()
def register_medicine_batch():
    """
    Register a new medicine batch with hash chain
    Required: batch_id, name, manufacturer, expiry_date
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if (user.user_type or '').lower() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json() or {}
        
        # Validate required fields
        required = ['batch_id', 'name', 'manufacturer']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if batch already exists
        if Medicine.query.filter_by(batch_id=data['batch_id']).first():
            return jsonify({'error': 'Batch ID already registered'}), 409
        
        # Create root hash
        root_hash = MedicineHashChain.create_initial_hash(
            data['batch_id'],
            data['name'],
            data['manufacturer']
        )
        
        # Create medicine record
        medicine = Medicine(
            batch_id=data['batch_id'],
            name=data['name'],
            manufacturer=data['manufacturer'],
            hash_chain_root=root_hash,
            expiry_date=datetime.fromisoformat(data['expiry_date']) if 'expiry_date' in data else None
        )
        
        db.session.add(medicine)
        # Ensure DB-generated/default primary key is available for FK usage below.
        db.session.flush()
        
        # Create initial supply chain record
        initial_data = {
            "batch_id": data["batch_id"],
            "medicine_name": data["name"],
            "manufacturer": data["manufacturer"],
            "timestamp": datetime.utcnow().isoformat(),
            "location": "Manufacturer",
            "handler": data["manufacturer"],
        }

        initial_record = SupplyChainRecord(
            medicine_id=medicine.id,
            previous_hash=None,
            current_data=json.dumps(initial_data, sort_keys=True),
            current_hash=root_hash,
            location="Manufacturer",
            handler=data["manufacturer"],
        )
        
        db.session.add(initial_record)
        db.session.commit()
        
        # Generate QR data
        qr_data = MedicineHashChain.generate_qr_data(data['batch_id'], root_hash)
        
        return jsonify({
            'message': 'Medicine batch registered successfully',
            'batch_id': data['batch_id'],
            'root_hash': root_hash,
            'qr_data': qr_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[MEDICINE][register_batch] Error: {str(e)}")
        return jsonify({'error': 'Failed to register medicine batch'}), 500

@medicine_bp.route('/add-supply-chain', methods=['POST'])
@jwt_required()
def add_supply_chain_record():
    """
    Add a step to medicine supply chain
    Required: batch_id, location, handler
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if (user.user_type or '').lower() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json() or {}
        
        required = ['batch_id', 'location', 'handler']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find medicine
        medicine = Medicine.query.filter_by(batch_id=data['batch_id']).first()
        if not medicine:
            return jsonify({'error': 'Medicine batch not found'}), 404
        
        # Get last supply chain record
        last_record = SupplyChainRecord.query.filter_by(medicine_id=medicine.id).order_by(
            SupplyChainRecord.timestamp.desc()
        ).first()
        
        previous_hash = last_record.current_hash if last_record else medicine.hash_chain_root
        
        # Create new chain entry
        new_entry = MedicineHashChain.add_to_chain(
            previous_hash,
            data['location'],
            data['handler']
        )
        
        # Save to database
        record = SupplyChainRecord(
            medicine_id=medicine.id,
            previous_hash=new_entry['previous_hash'],
            current_data=json.dumps(new_entry['current_data'], sort_keys=True),
            current_hash=new_entry['current_hash'],
            location=data['location'],
            handler=data['handler']
        )
        
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'message': 'Supply chain record added',
            'previous_hash': new_entry['previous_hash'],
            'current_hash': new_entry['current_hash'],
            'location': data['location'],
            'handler': data['handler']
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[MEDICINE][add_supply_chain] Error: {str(e)}")
        return jsonify({'error': 'Failed to add supply chain record'}), 500

@medicine_bp.route('/verify/<batch_id>', methods=['GET'])
def verify_medicine(batch_id):
    """
    Verify medicine authenticity and get supply chain
    """
    try:
        medicine = Medicine.query.filter_by(batch_id=batch_id).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine batch not found'}), 404
        
        # Get all supply chain records
        records = SupplyChainRecord.query.filter_by(medicine_id=medicine.id).order_by(
            SupplyChainRecord.timestamp.asc()
        ).all()
        
        # Format records for verification
        chain_records = []
        for record in records:
            parsed_data = record.current_data
            if isinstance(parsed_data, str):
                try:
                    parsed_data = json.loads(parsed_data)
                except json.JSONDecodeError:
                    parsed_data = ast.literal_eval(parsed_data)

            chain_records.append({
                'previous_hash': record.previous_hash,
                'current_data': parsed_data,
                'current_hash': record.current_hash
            })
        
        # Verify chain integrity
        verification = MedicineHashChain.verify_chain(chain_records, medicine.hash_chain_root)
        
        return jsonify({
            'batch_id': batch_id,
            'medicine_name': medicine.name,
            'manufacturer': medicine.manufacturer,
            'is_authentic': verification['is_authentic'],
            'chain_valid': verification['chain_valid'],
            'supply_chain': [record.to_dict() for record in records],
            'verification_details': verification['verification_details']
        }), 200
        
    except Exception as e:
        print(f"[MEDICINE][verify] Error: {str(e)}")
        return jsonify({'error': 'Failed to verify medicine'}), 500

@medicine_bp.route('/list-batches', methods=['GET'])
@jwt_required()
def list_medicine_batches():
    """
    List all medicine batches (admin feature)
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if (user.user_type or '').lower() != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        medicines = Medicine.query.paginate(page=page, per_page=per_page)
        
        return jsonify({
            'total': medicines.total,
            'pages': medicines.pages,
            'current_page': page,
            'medicines': [m.to_dict() for m in medicines.items]
        }), 200
        
    except Exception as e:
        print(f"[MEDICINE][list_batches] Error: {str(e)}")
        return jsonify({'error': 'Failed to list medicine batches'}), 500

@medicine_bp.route('/qr-generate/<batch_id>', methods=['GET'])
def generate_qr(batch_id):
    """
    Generate QR code data for medicine batch
    """
    try:
        medicine = Medicine.query.filter_by(batch_id=batch_id).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine batch not found'}), 404
        
        qr_data = MedicineHashChain.generate_qr_data(batch_id, medicine.hash_chain_root)
        
        return jsonify({
            'batch_id': batch_id,
            'qr_data': qr_data,
            'medicine_name': medicine.name
        }), 200
        
    except Exception as e:
        print(f"[MEDICINE][generate_qr] Error: {str(e)}")
        return jsonify({'error': 'Failed to generate QR data'}), 500
