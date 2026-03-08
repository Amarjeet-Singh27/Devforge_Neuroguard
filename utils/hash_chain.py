import hashlib
import json
from datetime import datetime

class MedicineHashChain:
    """
    Manages supply chain verification using SHA256 hash chains
    Ensures medicine authenticity and tamper-proof tracking
    """
    
    @staticmethod
    def create_initial_hash(batch_id, medicine_name, manufacturer):
        """
        Create the root hash for a new medicine batch
        This is the starting point of the hash chain
        """
        data = {
            'batch_id': batch_id,
            'medicine_name': medicine_name,
            'manufacturer': manufacturer,
            'timestamp': datetime.utcnow().isoformat(),
            'location': 'Manufacturer',
            'handler': manufacturer
        }
        
        hash_value = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return hash_value
    
    @staticmethod
    def add_to_chain(previous_hash, location, handler):
        """
        Add a new entry to the supply chain
        previous_hash: The hash from the previous step
        location: Current location in supply chain
        handler: Who handled at this step
        
        Returns: {
            'previous_hash': str,
            'current_data': dict,
            'current_hash': str
        }
        """
        current_data = {
            'previous_hash': previous_hash,
            'location': location,
            'handler': handler,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        hash_input = json.dumps({
            'previous_hash': previous_hash,
            'current_hash_input': json.dumps(current_data, sort_keys=True)
        }, sort_keys=True)
        
        current_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return {
            'previous_hash': previous_hash,
            'current_data': current_data,
            'current_hash': current_hash
        }
    
    @staticmethod
    def verify_chain(supply_chain_records, root_hash):
        """
        Verify the entire supply chain integrity
        
        supply_chain_records: List of records with 'previous_hash', 'current_data', 'current_hash'
        root_hash: The original root hash
        
        Returns: {
            'is_authentic': bool,
            'verification_details': list,
            'chain_valid': bool
        }
        """
        if not supply_chain_records:
            return {
                'is_authentic': False,
                'verification_details': [{'status': 'No records found', 'valid': False}],
                'chain_valid': False
            }
        
        verification_details = []
        current_hash = root_hash
        is_authentic = True

        for i, record in enumerate(supply_chain_records):
            # First record is the root entry produced by create_initial_hash.
            # Its stored hash must match the root hash exactly.
            if i == 0:
                record_valid = record['current_hash'] == root_hash
                if not record_valid:
                    is_authentic = False

                verification_details.append({
                    'step': i + 1,
                    'location': record['current_data'].get('location'),
                    'handler': record['current_data'].get('handler'),
                    'timestamp': record['current_data'].get('timestamp'),
                    'hash_valid': record_valid,
                    'stored_hash': record['current_hash'],
                    'computed_hash': root_hash
                })

                current_hash = record['current_hash']
                continue

            hash_input = json.dumps({
                'previous_hash': record['previous_hash'],
                'current_hash_input': json.dumps(record['current_data'], sort_keys=True)
            }, sort_keys=True)
            
            computed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            record_valid = computed_hash == record['current_hash']
            
            if not record_valid:
                is_authentic = False
            
            verification_details.append({
                'step': i + 1,
                'location': record['current_data'].get('location'),
                'handler': record['current_data'].get('handler'),
                'timestamp': record['current_data'].get('timestamp'),
                'hash_valid': record_valid,
                'stored_hash': record['current_hash'],
                'computed_hash': computed_hash
            })
            
            current_hash = record['current_hash']
        
        return {
            'is_authentic': is_authentic,
            'verification_details': verification_details,
            'chain_valid': is_authentic,
            'final_hash': current_hash
        }
    
    @staticmethod
    def generate_qr_data(batch_id, root_hash):
        """
        Generate QR code data for medicine batch
        This can be embedded in QR codes for scanning
        """
        return f"BATCH:{batch_id}|HASH:{root_hash}|VERIFY:{hashlib.sha256((batch_id + root_hash).encode()).hexdigest()[:16]}"
    
    @staticmethod
    def parse_qr_data(qr_string):
        """
        Parse QR code data to extract batch info
        """
        try:
            parts = qr_string.split('|')
            data = {}
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    data[key] = value
            return data
        except:
            return None
