def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"


def test_refresh_flow(client):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "adminpass123"},
    ).json()
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_refresh_rejects_access_token(client, admin_token):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": admin_token})
    assert response.status_code == 401


def test_unauthenticated_rejected(client):
    assert client.get("/api/v1/recognitions").status_code == 401
    assert client.get("/api/v1/cameras").status_code == 401


def test_viewer_cannot_create_user(client, viewer_headers):
    response = client.post(
        "/api/v1/users",
        json={"email": "x@example.com", "password": "password123", "role": "viewer"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_viewer_cannot_create_camera(client, viewer_headers):
    response = client.post(
        "/api/v1/cameras",
        json={"name": "nope", "rtsp_url": "rtsp://x"},
        headers=viewer_headers,
    )
    assert response.status_code == 403
