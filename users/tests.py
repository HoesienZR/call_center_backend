import requests
import json

# Settings
BASE_URL = "https://8000-iv9nvny36bk7nz25ctdns-e56203cc.manusvm.computer/api"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def test_login():
    """Test user login"""
    print("=== Testing user login ===")

    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 200:
            token = response.json().get('token')
            print(f"Token received: {token}")
            return token
        else:
            print("Login failed")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")
        return None


def test_api_with_token(token):
    """Test API access with token"""
    print("\n=== Testing API access with token ===")

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

    try:
        # Test retrieving the list of projects
        response = requests.get(f"{BASE_URL}/projects/", headers=headers)
        print(f"GET /projects/ - Status Code: {response.status_code}")

        if response.status_code == 200:
            print("API access successful")
            print(f"Number of projects: {len(response.json().get('results', []))}")
        else:
            print(f"API access error: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")


def test_api_without_token():
    """Test API access without token"""
    print("\n=== Testing API access without token ===")

    try:
        response = requests.get(f"{BASE_URL}/projects/")
        print(f"GET /projects/ without token - Status Code: {response.status_code}")

        if response.status_code in (401, 403):
            print("Access correctly denied (expected)")
        else:
            print("Problem: Access without token is possible!")

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")


def test_user_profile(token):
    """Test retrieving user profile"""
    print("\n=== Testing user profile retrieval ===")

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{BASE_URL}/auth/profile/", headers=headers)
        print(f"GET /auth/profile/ - Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"User profile: {response.json()}")
        else:
            print(f"Error retrieving profile: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error during request: {e}")


def main():
    """Main test function"""
    print("Starting Token Authentication system tests")
    print("=" * 50)

    # Test login
    token = test_login()

    if token:
        # Test API access with token
        test_api_with_token(token)

        # Test user profile
        test_user_profile(token)

    # Test access without token
    test_api_without_token()

    print("\n" + "=" * 50)
    print("All tests completed")


if __name__ == "__main__":
    main()
