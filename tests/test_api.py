def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_current_without_connection(client):
    response = client.get("/api/services/current?user_id=missing")
    assert response.status_code == 404
