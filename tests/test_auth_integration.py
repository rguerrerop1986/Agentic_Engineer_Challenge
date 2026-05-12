def test_login_success_returns_jwt(integration_harness) -> None:
    client = integration_harness.client
    response = client.post(
        "/auth/login",
        json={"email": "integration-test@example.com", "password": "test-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 20
