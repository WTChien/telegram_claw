def test_list_services(client):
    response = client.get("/api/services/list")
    assert response.status_code == 200
    payload = response.json()
    assert "services" in payload
    assert isinstance(payload["services"], list)


def test_preference_crud(client):
    save_resp = client.post(
        "/api/services/user/preference",
        json={
            "user_id": "u1",
            "preferred_port": 11434,
            "preferred_service": "Ollama",
        },
    )
    assert save_resp.status_code == 200

    get_resp = client.get("/api/services/user/preference?user_id=u1")
    assert get_resp.status_code == 200
    data = get_resp.json()["preference"]
    assert data["preferred_port"] == 11434
    assert data["preferred_service"] == "Ollama"
