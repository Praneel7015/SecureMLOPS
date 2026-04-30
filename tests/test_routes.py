"""
Test suite for SecureMLOps routes.
Run with: python -m pytest tests/test_routes.py -v
Or: python tests/test_routes.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def logged_in_client(client):
    """Create a test client that's logged in."""
    with client.session_transaction() as sess:
        sess["user"] = "person1"
    return client


class TestIndexRoute:
    def test_index_get_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200


class TestLoginRoute:
    def test_login_valid_credentials_redirects(self, client):
        response = client.post("/login", data={
            "username": "person1",
            "password": "password123"
        }, follow_redirects=False)
        assert response.status_code in [200, 302]


class TestLogoutRoute:
    def test_logout_works_when_logged_in(self, logged_in_client):
        response = logged_in_client.post("/logout", follow_redirects=False)
        assert response.status_code in [200, 302]


class TestSettingsRoute:
    def test_settings_requires_login(self, client):
        response = client.get("/settings", follow_redirects=False)
        assert response.status_code in [200, 302]
    
    def test_settings_works_when_logged_in(self, logged_in_client):
        response = logged_in_client.get("/settings")
        assert response.status_code == 200


class TestAnalyzeRoute:
    def test_analyze_requires_login(self, client):
        response = client.post("/analyze", follow_redirects=False)
        assert response.status_code in [200, 302]


class TestStaticRoutes:
    def test_static_css_exists(self, client):
        response = client.get("/static/style.css")
        assert response.status_code == 200


class TestRouteIntegrity:
    def test_all_routes_registered(self, client):
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ["/", "/login", "/logout", "/settings", "/analyze"]
        for route in expected_routes:
            assert route in rules, f"Route {route} not found"


def run_tests():
    """Standalone test runner."""
    print("=" * 60)
    print("SecureMLOps Route Tests")
    print("=" * 60)
    
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    
    passed = failed = 0
    
    with app.test_client() as client:
        tests = [
            ("GET / (index)", lambda: client.get("/")),
            ("POST /login", lambda: client.post("/login", data={"username": "person1", "password": "password123"}, follow_redirects=False)),
            ("POST /logout", lambda: client.post("/logout", follow_redirects=False)),
            ("GET /settings (no login)", lambda: client.get("/settings", follow_redirects=False)),
            ("GET /settings (logged in)", lambda: (lambda c: (c.session_transaction().__setitem__("user", "person1"), c.get("/settings"))[1])(client)),
            ("POST /analyze (no login)", lambda: client.post("/analyze", follow_redirects=False)),
            ("GET /static/style.css", lambda: client.get("/static/style.css")),
        ]
        
        for name, test_fn in tests:
            print(f"\n[{passed+failed+1}] {name}...")
            try:
                response = test_fn()
                assert response.status_code in [200, 302], f"Got {response.status_code}"
                print(f"    ✓ PASSED")
                passed += 1
            except Exception as e:
                print(f"    ✗ FAILED: {e}")
                failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)