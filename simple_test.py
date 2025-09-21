"""
Simple test script for Golden Turf Flask application.
"""
import requests
import time
import sys

def test_basic():
    """Test basic application functionality."""
    print("Testing Golden Turf Application...")
    print("Waiting 3 seconds for app to initialize...")
    time.sleep(3)

    try:
        # Test main page
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        if response.status_code == 200:
            print("✅ Application is running")
        else:
            print(f"❌ App returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect: {e}")
        return False

    try:
        # Test database
        from utils.database import get_db
        db = get_db()
        result = db.execute_query("SELECT COUNT(*) FROM users", fetchone=True)
        if result:
            print(f"✅ Database working, users: {result[0]}")
        else:
            print("❌ Database query failed")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

    try:
        # Test security
        from utils.security import get_security
        security = get_security()
        test_pass = "Test123!"
        hashed = security.hash_password(test_pass)
        if security.verify_password(test_pass, hashed):
            print("✅ Security features working")
        else:
            print("❌ Security test failed")
            return False
    except Exception as e:
        print(f"❌ Security test failed: {e}")
        return False

    print("✅ All basic tests passed!")
    return True

if __name__ == "__main__":
    success = test_basic()
    if success:
        print("\n🎉 Application is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some issues found.")
        sys.exit(1)
