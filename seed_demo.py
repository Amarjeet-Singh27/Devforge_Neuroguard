import json
import os
from datetime import datetime, timedelta

from app import create_app
from models import db, User, VoiceTest, Medicine, SupplyChainRecord
from utils.hash_chain import MedicineHashChain


DOCTOR_EMAIL = "demo.doctor@neuroguard.local"
PATIENT_EMAIL = "demo.patient@neuroguard.local"
DEFAULT_PASSWORD = "DemoPass123!"
DEMO_BATCH_ID = "DEMO-BATCH-001"


def ensure_user(email, full_name, user_type, age):
    user = User.query.filter_by(email=email).first()
    if user:
        return user, False

    user = User(
        email=email,
        full_name=full_name,
        user_type=user_type,
        age=age,
    )
    user.set_password(DEFAULT_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user, True


def ensure_voice_tests(patient_id):
    existing = VoiceTest.query.filter_by(patient_id=patient_id).count()
    if existing >= 3:
        return 0

    now = datetime.utcnow()
    samples = [
        ("Low", 24.0, 14.2, 18.8, 11.0, 8.4, "NORMAL: Keep periodic monitoring."),
        ("Medium", 58.0, 37.5, 55.2, 42.7, 39.4, "CAUTION: Schedule a doctor check-up soon."),
        ("High", 86.0, 76.8, 82.1, 74.4, 79.9, "URGENT: Consult a neurologist immediately."),
    ]

    created = 0
    for index, sample in enumerate(samples):
        risk_level, risk_score, slur, delay, freq, tremor, recommendation = sample
        test = VoiceTest(
            patient_id=patient_id,
            audio_filename=f"demo_{risk_level.lower()}_{index + 1}.wav",
            audio_path=os.path.join("uploads", f"demo_{risk_level.lower()}_{index + 1}.wav"),
            risk_level=risk_level,
            risk_score=risk_score,
            slurring_score=slur,
            speech_delay_score=delay,
            frequency_variation_score=freq,
            tremor_score=tremor,
            recommendations=recommendation,
            test_date=now - timedelta(days=(2 - index)),
        )
        db.session.add(test)
        created += 1

    db.session.commit()
    return created


def ensure_medicine_batch():
    medicine = Medicine.query.filter_by(batch_id=DEMO_BATCH_ID).first()
    if medicine:
        return medicine, 0

    root_hash = MedicineHashChain.create_initial_hash(
        DEMO_BATCH_ID, "Aspirin 500mg", "NeuroGuard Pharma"
    )

    medicine = Medicine(
        batch_id=DEMO_BATCH_ID,
        name="Aspirin 500mg",
        manufacturer="NeuroGuard Pharma",
        hash_chain_root=root_hash,
        expiry_date=datetime.utcnow() + timedelta(days=365),
    )
    db.session.add(medicine)
    db.session.flush()

    initial_data = {
        "batch_id": DEMO_BATCH_ID,
        "medicine_name": medicine.name,
        "manufacturer": medicine.manufacturer,
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Manufacturer",
        "handler": medicine.manufacturer,
    }
    db.session.add(
        SupplyChainRecord(
            medicine_id=medicine.id,
            previous_hash=None,
            current_data=json.dumps(initial_data, sort_keys=True),
            current_hash=root_hash,
            location="Manufacturer",
            handler=medicine.manufacturer,
        )
    )

    previous_hash = root_hash
    for location, handler in [
        ("Central Warehouse", "NeuroGuard Logistics"),
        ("City Pharmacy", "HealthPlus Pharmacy"),
    ]:
        entry = MedicineHashChain.add_to_chain(previous_hash, location, handler)
        db.session.add(
            SupplyChainRecord(
                medicine_id=medicine.id,
                previous_hash=entry["previous_hash"],
                current_data=json.dumps(entry["current_data"], sort_keys=True),
                current_hash=entry["current_hash"],
                location=location,
                handler=handler,
            )
        )
        previous_hash = entry["current_hash"]

    db.session.commit()
    return medicine, 3


def main():
    os.environ.setdefault("JWT_SECRET_KEY", "hackathon-demo-secret")
    app = create_app("development")

    with app.app_context():
        doctor, doctor_created = ensure_user(
            DOCTOR_EMAIL, "Demo Doctor", "doctor", age=38
        )
        patient, patient_created = ensure_user(
            PATIENT_EMAIL, "Demo Patient", "patient", age=29
        )
        tests_created = ensure_voice_tests(patient.id)
        medicine, chain_records_created = ensure_medicine_batch()

        print("Demo seed completed")
        print(f"Doctor created: {doctor_created} | email={doctor.email}")
        print(f"Patient created: {patient_created} | email={patient.email}")
        print(f"Default password for both: {DEFAULT_PASSWORD}")
        print(f"Voice tests added: {tests_created}")
        print(
            f"Medicine batch: {medicine.batch_id} | new supply chain records added: {chain_records_created}"
        )


if __name__ == "__main__":
    main()
