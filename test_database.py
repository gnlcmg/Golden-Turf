"""
Test script to verify database connection and basic functionality.
"""
import sqlite3
import os

def test_database():
    """Test database connection and basic operations."""
    db_path = os.environ.get('DATABASE_URI', 'sqlite:///users.db').replace('sqlite:///', '')

    print(f"Testing database connection to: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Test basic connection
        c.execute("SELECT 1")
        result = c.fetchone()
        print(f"✅ Database connection successful: {result}")

        # Check existing tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print(f"📊 Existing tables: {[table[0] for table in tables]}")

        # Check users table structure
        if 'users' in [table[0] for table in tables]:
            c.execute("PRAGMA table_info(users)")
            columns = c.fetchall()
            print("👤 Users table columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False

if __name__ == "__main__":
    test_database()
