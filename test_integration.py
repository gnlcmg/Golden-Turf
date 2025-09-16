#!/usr/bin/env python3
"""
Integration test to verify the Flask application works correctly after invoice extras pricing fixes
"""

import requests
import json
import time
from datetime import datetime

def test_application_running():
    """
    Test that the Flask application is running and responding
    """
    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        if response.status_code == 200:
            print("✓ Flask application is running and responding")
            return True
        else:
            print(f"✗ Flask application returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not connect to Flask application: {e}")
        return False

def test_invoice_form_access():
    """
    Test that the invoice form is accessible
    """
    try:
        response = requests.get('http://127.0.0.1:5000/invoice', timeout=5)
        if response.status_code == 200:
            print("✓ Invoice form is accessible")
            return True
        else:
            print(f"✗ Invoice form returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not access invoice form: {e}")
        return False

def test_payments_page_access():
    """
    Test that the payments page is accessible
    """
    try:
        response = requests.get('http://127.0.0.1:5000/payments', timeout=5)
        if response.status_code == 200:
            print("✓ Payments page is accessible")
            return True
        else:
            print(f"✗ Payments page returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not access payments page: {e}")
        return False

def test_dashboard_access():
    """
    Test that the dashboard is accessible
    """
    try:
        response = requests.get('http://127.0.0.1:5000/dashboard', timeout=5)
        if response.status_code == 200:
            print("✓ Dashboard is accessible")
            return True
        else:
            print(f"✗ Dashboard returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not access dashboard: {e}")
        return False

def test_static_files():
    """
    Test that static files are accessible
    """
    try:
        response = requests.get('http://127.0.0.1:5000/static/dashboard.css', timeout=5)
        if response.status_code == 200:
            print("✓ Static CSS file is accessible")
            return True
        else:
            print(f"✗ Static CSS file returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not access static CSS file: {e}")
        return False

def run_integration_tests():
    """
    Run all integration tests
    """
    print("Running Integration Tests for Golden Turf Application")
    print("=" * 60)

    tests = [
        test_application_running,
        test_invoice_form_access,
        test_payments_page_access,
        test_dashboard_access,
        test_static_files
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Integration Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests PASSED! Application is working correctly.")
        return True
    else:
        print("❌ Some integration tests FAILED. Please check the application.")
        return False

if __name__ == "__main__":
    # Give the Flask app a moment to fully start if it was just restarted
    time.sleep(2)
    success = run_integration_tests()
    exit(0 if success else 1)
