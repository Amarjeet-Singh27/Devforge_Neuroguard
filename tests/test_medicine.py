def test_medicine_register_add_supply_and_verify(client, create_user_and_token):
    token, _ = create_user_and_token(
        "doctor@example.com", "DoctorPass123!", "Doctor User", "doctor", 42
    )
    headers = {"Authorization": f"Bearer {token}"}

    batch_id = "TEST-BATCH-001"

    register_resp = client.post(
        "/api/medicine/register-batch",
        headers=headers,
        json={
            "batch_id": batch_id,
            "name": "Test Medicine 500mg",
            "manufacturer": "Test Pharma",
            "expiry_date": "2027-01-01",
        },
    )
    assert register_resp.status_code == 201
    register_data = register_resp.get_json()
    assert register_data["batch_id"] == batch_id
    assert "root_hash" in register_data

    supply_resp = client.post(
        "/api/medicine/add-supply-chain",
        headers=headers,
        json={
            "batch_id": batch_id,
            "location": "Warehouse A",
            "handler": "Logistics Team",
        },
    )
    assert supply_resp.status_code == 201

    verify_resp = client.get(f"/api/medicine/verify/{batch_id}")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.get_json()
    assert verify_data["batch_id"] == batch_id
    assert verify_data["is_authentic"] is True
    assert verify_data["chain_valid"] is True
    assert len(verify_data["supply_chain"]) >= 2
