import io
import json
from pathlib import Path

from app import create_app
from models import db


def run():
    app = create_app("testing")
    app.config.update(TESTING=True)

    results = []

    def check(name, condition, details=""):
        status = "PASS" if condition else "FAIL"
        results.append({"step": name, "status": status, "details": details})
        print(f"[{status}] {name} {details}")

    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()

    # 1) Register user
    email = "smoke.user@example.com"
    password = "SmokePass123!"
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Smoke User",
            "user_type": "patient",
            "age": 28,
        },
    )
    check("register", reg.status_code == 201, f"(status={reg.status_code})")

    # 2) Login
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    token = None
    if login.status_code == 200:
        token = login.get_json().get("access_token")
    check("login", login.status_code == 200 and bool(token), f"(status={login.status_code})")
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 3) Contact submit
    contact = client.post(
        "/api/contact",
        json={
            "name": "Smoke User",
            "email": email,
            "subject": "Smoke test",
            "message": "This is a smoke-test contact message.",
        },
    )
    check("contact_submit", contact.status_code == 201, f"(status={contact.status_code})")

    # 4) Contact list (auth)
    contact_list = client.get("/api/contact/list", headers=auth_headers)
    list_ok = contact_list.status_code == 200 and contact_list.get_json().get("total_messages", 0) >= 1
    check("contact_list", list_ok, f"(status={contact_list.status_code})")

    # 5) Medicine register + verify
    batch_id = "SMOKE-BATCH-001"
    med_reg = client.post(
        "/api/medicine/register-batch",
        headers=auth_headers,
        json={
            "batch_id": batch_id,
            "name": "SmokeMed",
            "manufacturer": "Smoke Pharma",
            "expiry_date": "2030-12-31",
        },
    )
    check("medicine_register", med_reg.status_code == 201, f"(status={med_reg.status_code})")

    med_verify = client.get(f"/api/medicine/verify/{batch_id}")
    verify_ok = med_verify.status_code == 200 and "is_authentic" in (med_verify.get_json() or {})
    check("medicine_verify", verify_ok, f"(status={med_verify.status_code})")

    # 6) Voice test upload + report PDF
    audio_path = Path("dataset/low/sample_low.wav")
    if not audio_path.exists():
        check("voice_test", False, "(sample audio file missing: dataset/low/sample_low.wav)")
        check("voice_pdf", False, "(skipped because voice test failed)")
    else:
        with audio_path.open("rb") as fh:
            data = {
                "audio": (io.BytesIO(fh.read()), "sample_low.wav")
            }
        voice_resp = client.post(
            "/api/voice/test",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        voice_ok = voice_resp.status_code == 201
        check("voice_test", voice_ok, f"(status={voice_resp.status_code})")

        if voice_ok:
            test_id = voice_resp.get_json().get("test_result", {}).get("id")
            pdf_resp = client.get(f"/api/voice/test/{test_id}/report.pdf", headers=auth_headers)
            pdf_ok = pdf_resp.status_code == 200 and pdf_resp.data.startswith(b"%PDF")
            check("voice_pdf", pdf_ok, f"(status={pdf_resp.status_code})")
        else:
            check("voice_pdf", False, "(skipped because voice test failed)")

    failed = [r for r in results if r["status"] == "FAIL"]
    print("\nSummary:")
    print(json.dumps(results, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
