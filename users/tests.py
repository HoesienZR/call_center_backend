import requests
import pytest

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


BASE_URL = "https://8000-iv9nvny36bk7nz25ctdns-e56203cc.manusvm.computer/api"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@pytest.fixture(scope="session")
def token():
    """Fixture to get authentication token once per test session"""
    login_data = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json().get("token")
    assert token is not None, "Token not received"
    return token

def test_api_with_token(token):
    """Test accessing the projects API with a valid token"""
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(f"{BASE_URL}/projects/", headers=headers)
    assert response.status_code == 200, f"API access failed: {response.text}"
    data = response.json()
    assert "results" in data, "No 'results' in response"

def test_api_without_token():
    """Test accessing the projects API without a token"""
    response = requests.get(f"{BASE_URL}/projects/")
    assert response.status_code in (401, 403), "Access without token should be denied"

def test_user_profile(token):
    """Test retrieving user profile"""
    headers = {"Authorization": f"Token {token}"}
    response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
    assert response.status_code == 200, f"Failed to get profile: {response.text}"
    data = response.json()
    assert "username" in data, "Profile response missing 'username'"
