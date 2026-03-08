from datetime import datetime

from models import db, VoiceTest


def test_voice_stats_and_history_empty_state(client, create_user_and_token):
    token, _ = create_user_and_token(
        "voice.patient@example.com", "VoicePass123!", "Voice Patient", "patient", 31
    )
    headers = {"Authorization": f"Bearer {token}"}

    stats_resp = client.get("/api/voice/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json()
    assert stats_data["total_tests"] == 0
    assert stats_data["average_risk_score"] == 0
    assert stats_data["average_stress_score"] == 0
    assert stats_data["risk_distribution"] == {}
    assert stats_data["stress_distribution"] == {}

    history_resp = client.get("/api/voice/history", headers=headers)
    assert history_resp.status_code == 200
    history_data = history_resp.get_json()
    assert history_data["total_tests"] == 0
    assert history_data["tests"] == []


def test_voice_test_to_dict_contains_detailed_report():
    voice_test = VoiceTest(
        patient_id="patient-1",
        audio_filename="demo.wav",
        audio_path="uploads/demo.wav",
        risk_level="Medium",
        risk_score=60.0,
        slurring_score=52.3,
        speech_delay_score=41.2,
        frequency_variation_score=37.8,
        tremor_score=18.4,
        recommendations="Schedule a follow-up check within 1-2 weeks.",
        test_date=datetime.utcnow(),
    )

    payload = voice_test.to_dict()

    assert payload["stress_level"] == "Medium"
    assert payload["stress_score"] == 60.0
    assert "detailed_report" in payload
    assert payload["detailed_report"]["stress_level"] == "Medium"
    assert len(payload["detailed_report"]["metric_breakdown"]) == 4


def test_download_voice_pdf_report(client, app, create_user_and_token):
    token, user = create_user_and_token(
        "pdf.patient@example.com", "VoicePass123!", "PDF Patient", "patient", 30
    )
    headers = {"Authorization": f"Bearer {token}"}

    with app.app_context():
        voice_test = VoiceTest(
            patient_id=user["id"],
            audio_filename="sample.wav",
            audio_path="uploads/sample.wav",
            risk_level="Low",
            risk_score=25.0,
            slurring_score=10.0,
            speech_delay_score=12.0,
            frequency_variation_score=15.0,
            tremor_score=7.0,
            recommendations="Routine monitoring recommended.",
            test_date=datetime.utcnow(),
        )
        db.session.add(voice_test)
        db.session.commit()
        test_id = voice_test.id

    response = client.get(f"/api/voice/test/{test_id}/report.pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/pdf")
    assert response.data.startswith(b"%PDF-1.4")
