from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'patient' or 'admin'
    age = db.Column(db.Integer)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    voice_tests = db.relationship('VoiceTest', backref='patient', lazy=True, foreign_keys='VoiceTest.patient_id')
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True, foreign_keys='Prescription.doctor_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'user_type': self.user_type,
            'created_at': self.created_at.isoformat()
        }


class VoiceTest(db.Model):
    __tablename__ = 'voice_tests'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    audio_filename = db.Column(db.String(255), nullable=False)
    audio_path = db.Column(db.String(500), nullable=False)
    
    # Analysis Results
    risk_level = db.Column(db.String(20))  # 'Low', 'Medium', 'High'
    risk_score = db.Column(db.Float)  # 0-100
    slurring_score = db.Column(db.Float)
    speech_delay_score = db.Column(db.Float)
    frequency_variation_score = db.Column(db.Float)
    tremor_score = db.Column(db.Float)
    
    # Additional info
    test_date = db.Column(db.DateTime, default=datetime.utcnow)
    recommendations = db.Column(db.Text)
    notes = db.Column(db.Text)

    @staticmethod
    def _metric_band(score):
        if score >= 67:
            return "High"
        if score >= 34:
            return "Moderate"
        return "Low"

    @classmethod
    def _metric_entry(cls, name, score, low_note, moderate_note, high_note):
        band = cls._metric_band(score)
        notes = {
            "Low": low_note,
            "Moderate": moderate_note,
            "High": high_note,
        }
        return {
            "metric": name,
            "score": round(float(score), 2),
            "band": band,
            "interpretation": notes[band],
        }

    @staticmethod
    def _metric_count_by_band(metric_breakdown, band):
        return sum(1 for metric in metric_breakdown if metric.get("band") == band)

    @classmethod
    def _calculate_confidence_score(cls, stress_level, stress_score, metric_breakdown):
        """
        Derive confidence from agreement + consistency instead of fixed buckets.
        This creates better spread across reports while remaining deterministic.
        """
        high_count = cls._metric_count_by_band(metric_breakdown, "High")
        moderate_count = cls._metric_count_by_band(metric_breakdown, "Moderate")
        low_count = cls._metric_count_by_band(metric_breakdown, "Low")
        metric_scores = [float(metric.get("score", 0.0)) for metric in metric_breakdown] or [0.0]

        average_metric_score = sum(metric_scores) / len(metric_scores)
        score_gap = abs(float(stress_score or 0.0) - average_metric_score)
        alignment = max(0.0, 1.0 - (score_gap / 100.0))

        # High dispersion across biomarkers lowers confidence.
        mean_score = average_metric_score
        variance = sum((score - mean_score) ** 2 for score in metric_scores) / len(metric_scores)
        std_dev = variance ** 0.5
        consistency = max(0.0, 1.0 - (std_dev / 35.0))

        if stress_level == "High":
            agreement = ((high_count * 2) + moderate_count) / 8.0
        elif stress_level == "Medium":
            agreement = ((moderate_count * 2) + min(high_count, 1) + min(low_count, 1)) / 6.0
        elif stress_level == "Low":
            agreement = ((low_count * 2) + moderate_count) / 8.0
        else:
            agreement = 0.0

        confidence = 40 + (30 * alignment) + (20 * consistency) + (10 * agreement)
        return round(max(50.0, min(95.0, float(confidence))), 2)

    @staticmethod
    def _confidence_band(confidence_score):
        if confidence_score >= 80:
            return "High"
        if confidence_score >= 65:
            return "Moderate"
        return "Low"

    @staticmethod
    def _build_improvement_suggestions(metric_breakdown):
        suggestions = []
        for metric in metric_breakdown:
            name = metric.get("metric")
            band = metric.get("band")
            if band == "Low":
                continue

            if name == "Slurring":
                suggestions.append(
                    "Practice slow articulation drills (read aloud for 5-10 minutes daily)."
                )
            elif name == "Speech Delay":
                suggestions.append(
                    "Use paced speaking: inhale, pause briefly, and complete short sentences."
                )
            elif name == "Frequency Variation":
                suggestions.append(
                    "Add gentle vocal warm-ups (humming, pitch glides) before speaking tasks."
                )
            elif name == "Tremor Pattern":
                suggestions.append(
                    "Reduce stimulants, hydrate well, and repeat testing after rest."
                )

        if not suggestions:
            suggestions.append(
                "Maintain current routine and re-test weekly for trend tracking."
            )
        else:
            suggestions.append(
                "Record tests in a quiet room with a steady microphone distance for better consistency."
            )

        return suggestions[:4]

    def _build_detailed_report(self):
        slurring = float(self.slurring_score or 0)
        delay = float(self.speech_delay_score or 0)
        variation = float(self.frequency_variation_score or 0)
        tremor = float(self.tremor_score or 0)
        stress_score = float(self.risk_score or 0)
        # Keep report label aligned with numeric score, even for legacy rows.
        if stress_score >= 66:
            stress_level = "High"
        elif stress_score >= 33:
            stress_level = "Medium"
        else:
            stress_level = "Low"

        metric_breakdown = [
            self._metric_entry(
                "Slurring",
                slurring,
                "Speech articulation appears stable with minimal slurring markers.",
                "Mild articulation instability detected. Repeat test in a quiet environment.",
                "Strong slurring indicators detected in this sample.",
            ),
            self._metric_entry(
                "Speech Delay",
                delay,
                "Speech timing appears consistent.",
                "Noticeable pause/timing variation detected.",
                "Frequent delay/pausing markers detected.",
            ),
            self._metric_entry(
                "Frequency Variation",
                variation,
                "Pitch and frequency variation are within expected range.",
                "Moderate pitch instability detected.",
                "High vocal frequency instability detected.",
            ),
            self._metric_entry(
                "Tremor Pattern",
                tremor,
                "Low tremor-like activity detected.",
                "Moderate tremor-like pattern detected.",
                "High tremor-like activity detected.",
            ),
        ]

        confidence_score = self._calculate_confidence_score(stress_level, stress_score, metric_breakdown)
        confidence_band = self._confidence_band(confidence_score)
        improvement_suggestions = self._build_improvement_suggestions(metric_breakdown)

        concerns = [m["metric"] for m in metric_breakdown if m["band"] == "High"]
        if not concerns:
            concerns = [m["metric"] for m in metric_breakdown if m["band"] == "Moderate"][:2]

        if stress_level == "High":
            actions = [
                "Book a clinical consultation as early as possible.",
                "Share this report and recent symptoms with your doctor.",
                "Repeat voice test in 24-48 hours for consistency tracking.",
            ]
            follow_up = "Immediate to 3 days"
            headline = "High stress indicators detected from voice biomarkers."
        elif stress_level == "Medium":
            actions = [
                "Schedule a doctor follow-up within 1-2 weeks.",
                "Track hydration, sleep, and stress triggers daily.",
                "Repeat voice test after rest in a low-noise setting.",
            ]
            follow_up = "Within 1-2 weeks"
            headline = "Moderate stress indicators detected."
        else:
            actions = [
                "Maintain routine wellness and stress-management habits.",
                "Repeat screening weekly or when symptoms change.",
                "Continue monitoring if speech or mood patterns change.",
            ]
            follow_up = "Routine monthly monitoring"
            headline = "Low stress indicators in current voice sample."

        return {
            "headline": headline,
            "stress_level": stress_level,
            "stress_score": round(stress_score, 2),
            "confidence_score": confidence_score,
            "confidence_band": confidence_band,
            "summary": self.recommendations or "",
            "primary_concerns": concerns,
            "metric_breakdown": metric_breakdown,
            "recommended_actions": actions,
            "improvement_suggestions": improvement_suggestions,
            "follow_up_window": follow_up,
            "disclaimer": (
                "This AI voice report is a screening aid, not a medical diagnosis. "
                "Consult a licensed clinician for clinical decisions."
            ),
        }
    
    def to_dict(self):
        detailed_report = self._build_detailed_report()
        display_level = detailed_report.get('stress_level', self.risk_level)
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'risk_level': display_level,
            'risk_score': self.risk_score,
            'stress_level': display_level,
            'stress_score': self.risk_score,
            'test_date': self.test_date.isoformat(),
            'slurring_score': self.slurring_score,
            'speech_delay_score': self.speech_delay_score,
            'frequency_variation_score': self.frequency_variation_score,
            'tremor_score': self.tremor_score,
            'recommendations': self.recommendations,
            'confidence_score': detailed_report.get('confidence_score', 0),
            'confidence_band': detailed_report.get('confidence_band', 'Low'),
            'improvement_suggestions': detailed_report.get('improvement_suggestions', []),
            'detailed_report': detailed_report
        }


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    doctor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    voice_test_id = db.Column(db.String(36), db.ForeignKey('voice_tests.id'), nullable=True)
    
    prescription_file = db.Column(db.String(500))
    issued_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    status = db.Column(db.String(20), default='active')  # 'active', 'expired', 'cancelled'
    notes = db.Column(db.Text)
    
    # Relationships
    medicines = db.relationship('PrescriptionMedicine', backref='prescription', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'issued_date': self.issued_date.isoformat(),
            'status': self.status,
            'medicines': [m.to_dict() for m in self.medicines]
        }


class Medicine(db.Model):
    __tablename__ = 'medicines'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    manufacturer = db.Column(db.String(255), nullable=False)
    
    hash_chain_root = db.Column(db.String(500), nullable=False)  # Root hash
    is_verified = db.Column(db.Boolean, default=True)
    
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    # Relationships
    supply_chain = db.relationship('SupplyChainRecord', backref='medicine', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'name': self.name,
            'manufacturer': self.manufacturer,
            'is_verified': self.is_verified,
            'supply_chain': [s.to_dict() for s in self.supply_chain]
        }


class PrescriptionMedicine(db.Model):
    __tablename__ = 'prescription_medicines'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prescription_id = db.Column(db.String(36), db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_batch_id = db.Column(db.String(100), db.ForeignKey('medicines.batch_id'), nullable=False)
    
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))  # e.g., "Once daily", "Twice daily"
    duration = db.Column(db.String(100))  # e.g., "7 days", "2 weeks"
    
    def to_dict(self):
        return {
            'id': self.id,
            'medicine_batch_id': self.medicine_batch_id,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration
        }


class SupplyChainRecord(db.Model):
    __tablename__ = 'supply_chain_records'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medicine_id = db.Column(db.String(36), db.ForeignKey('medicines.id'), nullable=False, index=True)
    
    previous_hash = db.Column(db.String(500), nullable=True)
    current_data = db.Column(db.Text, nullable=False)  # JSON: location, timestamp, handler
    current_hash = db.Column(db.String(500), nullable=False)
    
    location = db.Column(db.String(255))
    handler = db.Column(db.String(255))  # Manufacturer, Supplier, Pharmacy, Patient
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'previous_hash': self.previous_hash,
            'current_hash': self.current_hash,
            'location': self.location,
            'handler': self.handler,
            'timestamp': self.timestamp.isoformat()
        }


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='new', nullable=False)  # new, reviewed, closed

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
        }
