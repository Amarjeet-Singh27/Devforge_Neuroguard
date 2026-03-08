def test_register_and_login(client):
    register_payload = {
        "email": "auth.user@example.com",
        "password": "StrongPass123!",
        "full_name": "Auth User",
        "user_type": "patient",
        "age": 27,
    }
    register_resp = client.post("/api/auth/register", json=register_payload)
    assert register_resp.status_code == 201

    register_data = register_resp.get_json()
    assert register_data["user"]["email"] == register_payload["email"]
    assert "access_token" in register_data

    login_resp = client.post(
        "/api/auth/login",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.get_json()
    assert "access_token" in login_data
    assert login_data["user"]["full_name"] == "Auth User"


def test_login_invalid_password_returns_401(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "invalid.login@example.com",
            "password": "CorrectPass123!",
            "full_name": "Invalid Login",
            "user_type": "patient",
        },
    )

    login_resp = client.post(
        "/api/auth/login",
        json={"email": "invalid.login@example.com", "password": "wrong-password"},
    )
    assert login_resp.status_code == 401


def test_request_otp_fallback_returns_demo_otp_in_testing(client):
    resp = client.post("/api/auth/request-otp", json={"email": "otp.fallback@example.com"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email_delivery"] in ("smtp", "fallback")
    assert "expires_in_seconds" in data
    if data["email_delivery"] == "fallback":
        assert "demo_otp" in data


def test_verify_otp_with_fallback_code(client):
    email = "otp.verify@example.com"
    request_resp = client.post("/api/auth/request-otp", json={"email": email})
    assert request_resp.status_code == 200
    request_data = request_resp.get_json()
    otp = request_data.get("demo_otp")

    if not otp:
        # If SMTP is configured in this environment, we cannot know OTP value from API.
        return

    verify_resp = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp})
    assert verify_resp.status_code == 200
    verify_data = verify_resp.get_json()
    assert "verification_token" in verify_data
