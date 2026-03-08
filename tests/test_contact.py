def test_submit_contact_message_success(client):
    payload = {
        "name": "Hackathon User",
        "email": "hackathon@example.com",
        "subject": "Need help",
        "message": "Please contact me regarding the demo.",
    }
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 201

    data = response.get_json()
    assert data["message"] == "Contact message saved successfully"
    assert data["contact"]["email"] == "hackathon@example.com"
    assert data["contact"]["subject"] == "Need help"


def test_submit_contact_message_missing_fields(client):
    response = client.post("/api/contact", json={"name": "Only name"})
    assert response.status_code == 400
    assert "required" in response.get_json()["error"]


def test_list_contact_messages_requires_auth(client):
    response = client.get("/api/contact/list")
    assert response.status_code == 401


def test_list_contact_messages_with_auth(client, create_user_and_token):
    token, _ = create_user_and_token(
        "contact.admin@example.com", "ContactPass123!", "Contact Admin", "doctor", 35
    )
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/contact",
        json={
            "name": "Viewer",
            "email": "viewer@example.com",
            "subject": "Question",
            "message": "Can you share updates?",
        },
    )

    response = client.get("/api/contact/list", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_messages"] >= 1
    assert any(item["email"] == "viewer@example.com" for item in data["messages"])
