from fastapi.testclient import TestClient
from main import app
import pytest
import uuid

client = TestClient(app)

@pytest.fixture(scope="session")
def auth_headers():
    username = f"test-{uuid.uuid4()}"
    password = "testpass123"
    client.post("/signup", json={"username": username, "password": password})
    response = client.post("/login", json={"username": username, "password": password})
    print(response.status_code, response.json())
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_property(auth_headers):
    response = client.post("/properties", json={
        "name": "Test Tower",
        "address": "123 Test St",
        "city": "Austin",
        "square_ft": 2300,
        "floors": 10,
        "market_value": 5000000
    }, headers=auth_headers)
    prop = response.json()
    yield prop
    client.delete(f"/properties/{prop['id']}", headers=auth_headers)

@pytest.fixture
def sample_lease(sample_property, auth_headers):
    response = client.post(f"/properties/{sample_property['id']}/leases", json={
        "tenant_name": "Haggy",
        "start_date": "2026-10-05",
        "end_date": "2026-11-10",
        "monthly_rent": 5000,
        "leased_sqft": 300
    }, headers=auth_headers)
    lease = response.json()
    yield lease
    client.delete(f"/leases/{lease['id']}", headers=auth_headers)

def test_get_lease(sample_property, sample_lease, auth_headers):
    response = client.get(f"/properties/{sample_property['id']}/leases", headers=auth_headers)
    assert response.status_code == 200

def test_revenue_shape(sample_property, auth_headers):
    response = client.get(f"/properties/{sample_property['id']}/revenue", headers=auth_headers)
    assert response.status_code == 200
    assert "total_revenue" in response.json()

def test_get_properties(auth_headers):
    response = client.get("/properties", headers=auth_headers)
    assert response.status_code == 200

def test_get_property(sample_property, auth_headers):
    response = client.get(f"/properties/{sample_property['id']}", headers=auth_headers)
    assert response.status_code == 200

def test_property_not_found(auth_headers):
    response = client.get("/properties/999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Property not found"

def test_delete_property_with_lease(sample_lease, sample_property, auth_headers):
    response = client.delete(f"/properties/{sample_property['id']}", headers=auth_headers)
    assert response.status_code == 409

def test_properties_requires_auth():
    response = client.get("/properties")
    assert response.status_code == 401