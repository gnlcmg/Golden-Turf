import sqlite3
import os
from app import app
from flask import session
import requests
import time

def reset_database():
    """Reset the database to a clean state"""
    if os.path.exists('users.db'):
        os.remove('users.db')
    
    # Initialize database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        reset_token TEXT,
        token_expiry TEXT,
        role TEXT DEFAULT 'user',
        verification_code TEXT,
        permissions TEXT DEFAULT ''
    )''')
    conn.commit()
    conn.close()
    print("✓ Database reset successfully")

def check_user_count():
    """Check current user count and admin count"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = c.fetchone()[0]
    c.execute('SELECT id, name, email, role FROM users ORDER BY id')
    users = c.fetchall()
    conn.close()
    return user_count, admin_count, users

def simulate_register(name, email, password):
    """Simulate user registration"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check current user count (same logic as in app.py)
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    
    # Determine role and permissions (same logic as in app.py)
    if user_count == 0:
        role = 'admin'
        permissions = 'dashboard,payments,clients,calendar,products'
        print(f"  → First user, making admin with full permissions")
    else:
        role = 'user'
        permissions = ''
        print(f"  → Additional user, making regular user")
    
    try:
        # Simple password hash for testing (not using bcrypt for simplicity)
        hashed_password = f"hashed_{password}"
        c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                  (name, email, hashed_password, role, permissions))
        conn.commit()
        user_id = c.lastrowid
        print(f"  ✓ User registered: ID={user_id}, Name={name}, Role={role}")
        conn.close()
        return user_id, role
    except sqlite3.IntegrityError:
        print(f"  ✗ Registration failed: Email {email} already exists")
        conn.close()
        return None, None

def simulate_admin_add_user(name, email, password):
    """Simulate admin manually adding a user"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Admins always add users as regular users (not admins)
    role = 'user'
    permissions = ''
    
    try:
        hashed_password = f"hashed_{password}"
        c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                  (name, email, hashed_password, role, permissions))
        conn.commit()
        user_id = c.lastrowid
        print(f"  ✓ Admin added user: ID={user_id}, Name={name}, Role={role}")
        conn.close()
        return user_id, role
    except sqlite3.IntegrityError:
        print(f"  ✗ Add user failed: Email {email} already exists")
        conn.close()
        return None, None

def simulate_make_admin(user_id):
    """Simulate making a user admin"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
              ('admin', 'dashboard,payments,clients,calendar,products', user_id))
    conn.commit()
    print(f"  ✓ User ID {user_id} promoted to admin")
    conn.close()

def simulate_delete_user(user_id_to_delete, deleter_is_self=False):
    """Simulate user deletion with reordering logic from app.py"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Get user info before deletion
    c.execute('SELECT name, role FROM users WHERE id = ?', (user_id_to_delete,))
    user_info = c.fetchone()
    if not user_info:
        print(f"  ✗ User ID {user_id_to_delete} not found")
        conn.close()
        return
    
    user_name, user_role = user_info
    print(f"  → Deleting user ID {user_id_to_delete} ({user_name}, {user_role})")
    
    # Delete the user
    c.execute('DELETE FROM users WHERE id = ?', (user_id_to_delete,))
    conn.commit()
    
    # Reorder IDs sequentially (same logic as in app.py)
    c.execute('SELECT id FROM users ORDER BY id')
    users = c.fetchall()
    for index, user in enumerate(users, start=1):
        c.execute('UPDATE users SET id = ? WHERE id = ?', (index, user[0]))
    conn.commit()
    
    # Reset the sqlite_sequence
    c.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name='users'")
    conn.commit()
    
    # Check if any admins remain
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = c.fetchone()[0]
    
    if admin_count == 0:
        print(f"  → No admins remaining, promoting user ID 1 to admin")
        c.execute('SELECT id FROM users WHERE id = 1')
        user1 = c.fetchone()
        if user1:
            c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                      ('admin', 'dashboard,payments,clients,calendar,products', 1))
            conn.commit()
            print(f"  ✓ User ID 1 promoted to admin")
        else:
            print(f"  ! No user ID 1 exists to promote")
    
    print(f"  ✓ User deleted successfully")
    if deleter_is_self:
        print(f"  → User deleted themselves, would be logged out")
    
    conn.close()

def ensure_user_1_admin():
    """Ensure user ID 1 is always admin"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, role FROM users WHERE id = 1')
    user1 = c.fetchone()
    if user1:
        if user1[1] != 'admin':
            c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                      ('admin', 'dashboard,payments,clients,calendar,products', 1))
            conn.commit()
            print(f"  ✓ Enforced: User ID 1 is now admin")
        else:
            print(f"  ✓ User ID 1 is already admin")
    else:
        print(f"  ! No user ID 1 exists")
    conn.close()

def print_current_state():
    """Print current database state"""
    user_count, admin_count, users = check_user_count()
    print(f"\n📊 Current State: {user_count} users, {admin_count} admins")
    if users:
        for user in users:
            print(f"   ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    else:
        print("   No users in database")
    print("-" * 60)

def run_comprehensive_test():
    """Run all test scenarios"""
    print("🔬 COMPREHENSIVE USER SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: First user registration (should become admin)
    print("\n1️⃣  TEST: First user registration (no existing users)")
    reset_database()
    simulate_register("First User", "first@test.com", "password123")
    print_current_state()
    ensure_user_1_admin()  # Test requirement 5
    
    # Test 2: Second user registration (should be regular user)
    print("\n2️⃣  TEST: Second user registration (admin exists)")
    simulate_register("Second User", "second@test.com", "password123")
    print_current_state()
    
    # Test 3: Admin adds users manually (should be regular users)
    print("\n3️⃣  TEST: Admin manually adds users")
    simulate_admin_add_user("Third User", "third@test.com", "password123")
    simulate_admin_add_user("Fourth User", "fourth@test.com", "password123")
    print_current_state()
    
    # Test 4: Admin makes another user admin
    print("\n4️⃣  TEST: Admin promotes user ID 2 to admin")
    simulate_make_admin(2)
    print_current_state()
    
    # Test 5: Admin deletes themselves (multiple admins exist)
    print("\n5️⃣  TEST: Admin deletes themselves (other admins exist)")
    simulate_delete_user(2, deleter_is_self=True)  # Second user was admin
    print_current_state()
    
    # Test 6: Try to demote user ID 1 (should not be allowed)
    print("\n6️⃣  TEST: Ensure user ID 1 cannot be demoted from admin")
    ensure_user_1_admin()
    print_current_state()
    
    # Test 7: Delete all other users, leaving only ID 1
    print("\n7️⃣  TEST: Delete other users, leaving only user ID 1")
    user_count, admin_count, users = check_user_count()
    for user in users:
        if user[0] != 1:  # Don't delete user ID 1
            simulate_delete_user(user[0])
    print_current_state()
    
    # Test 8: Start fresh and test admin deletion with auto-promotion
    print("\n8️⃣  TEST: Admin deletion with auto-promotion to user ID 1")
    reset_database()
    simulate_register("Admin User", "admin@test.com", "password123")  # Will be ID 1, admin
    simulate_register("Regular User", "regular@test.com", "password123")  # Will be ID 2, user
    simulate_make_admin(2)  # Make user 2 admin
    # Now delete the original admin (ID 1), user 2 should become ID 1 and stay admin
    simulate_delete_user(1)
    print_current_state()
    ensure_user_1_admin()  # Ensure new ID 1 is admin
    
    print("\n✅ COMPREHENSIVE TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_comprehensive_test()