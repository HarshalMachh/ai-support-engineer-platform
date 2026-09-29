from app.core.security import create_access_token
from tests.conftest import TEST_PASSWORD, auth_headers


def test_register_creates_customer_and_returns_token(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "New User", "email": "New.User@Customer.dev", "password": "supersecret1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "new.user@customer.dev"
    assert body["user"]["role"] == "CUSTOMER"
    assert "password_hash" not in body["user"]
    assert "password" not in body["user"]


def test_register_rejects_duplicate_email(client, customer):
    response = client.post(
        "/api/auth/register",
        json={"name": "Carol Again", "email": customer.email, "password": "supersecret1"},
    )
    assert response.status_code == 409


def test_register_validates_input(client):
    response = client.post("/api/auth/register", json={"name": "X", "email": "not-an-email", "password": "short"})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_password_is_hashed(db, client):
    client.post("/api/auth/register", json={"name": "Hash Check", "email": "hash@customer.dev", "password": "supersecret1"})
    from app.models import User

    user = db.query(User).filter_by(email="hash@customer.dev").one()
    assert user.password_hash != "supersecret1"
    assert user.password_hash.startswith("$2")


def test_login_success(client, agent):
    response = client.post("/api/auth/login", json={"email": agent.email, "password": TEST_PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "AGENT"


def test_login_invalid_password(client, agent):
    response = client.post("/api/auth/login", json={"email": agent.email, "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(client):
    response = client.post("/api/auth/login", json={"email": "ghost@customer.dev", "password": "whatever1"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token(client, customer):
    response = client.get("/api/auth/me", headers=auth_headers(customer))
    assert response.status_code == 200
    assert response.json()["email"] == customer.email


def test_me_with_expired_token(client, customer):
    token = create_access_token(customer.id, customer.role.value, expires_minutes=-1)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


def test_me_with_tampered_token(client, customer):
    token = create_access_token(customer.id, customer.role.value) + "tampered"
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_role_restrictions(client, customer, agent, admin):
    assert client.get("/api/users", headers=auth_headers(customer)).status_code == 403
    assert client.get("/api/users", headers=auth_headers(agent)).status_code == 403
    assert client.get("/api/users", headers=auth_headers(admin)).status_code == 200
    assert client.get("/api/analytics/tickets", headers=auth_headers(customer)).status_code == 403
    assert client.get("/api/analytics/tickets", headers=auth_headers(agent)).status_code == 200
    assert client.get("/api/knowledge/documents", headers=auth_headers(customer)).status_code == 403


def test_admin_can_filter_users_by_role(client, customer, agent, admin):
    response = client.get("/api/users", params={"role": "AGENT"}, headers=auth_headers(admin))
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()["items"]]
    assert emails == [agent.email]
