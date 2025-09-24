#!/usr/bin/env python3
"""
Test script to verify admin deletion and promotion functionality
"""

import sqlite3
import requests
import json

def check_database_state():
    """Check current state of users database"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        conn.close()
        
        print("📋 Current Database State:")
        print("-" * 50)
        admins = []
        regular_users = []
        
        for user in users:
            user_info = f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}"
            if user[3] == 'admin':
                admins.append(user)
                print(f"👑 ADMIN - {user_info}")
            else:
                regular_users.append(user)
                print(f"👤 USER  - {user_info}")
        
        print(f"\n📊 Summary: {len(admins)} admin(s), {len(regular_users)} regular user(s)")
        return admins, regular_users
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return [], []

def test_authentication():
    """Test authentication with different user types"""
    print("\n🔐 Testing Authentication...")
    print("-" * 30)
    
    test_credentials = [
        ('mahi.gohil3695@gmail.com', 'test123', 'Original Admin (bcrypt)'),
        ('test1@example.com', 'password123', 'Manual User 1 (plain text)'),
        ('test2@example.com', 'mypassword', 'Manual User 2 (plain text)'),
        ('admin@test.com', 'admin123', 'Manual Admin (plain text)')
    ]
    
    for email, password, description in test_credentials:
        try:
            # Test login via API call
            response = requests.post('http://127.0.0.1:5000/login', 
                                   data={'email': email, 'password': password},
                                   allow_redirects=False)
            
            if response.status_code == 302:  # Redirect means successful login
                print(f"✅ {description}: Login successful")
            else:
                print(f"❌ {description}: Login failed")
                
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {description}: Could not connect to Flask app")
        except Exception as e:
            print(f"❌ {description}: Error - {e}")

def simulate_admin_self_deletion():
    """Simulate what happens when admin deletes themselves"""
    print("\n🗑️  Simulating Admin Self-Deletion...")
    print("-" * 40)
    
    admins, users = check_database_state()
    
    if len(admins) < 1:
        print("❌ No admin users found to test deletion")
        return
    
    # Find admin with highest ID (most recent)
    admin_to_delete = max(admins, key=lambda x: x[0])
    print(f"🎯 Target for deletion: {admin_to_delete[1]} (ID: {admin_to_delete[0]})")
    
    if len(admins) == 1:
        print("⚠️  This is the only admin - next user should be promoted")
        next_users = [u for u in users if u[0] > admin_to_delete[0]]
        if next_users:
            next_user = min(next_users, key=lambda x: x[0])
            print(f"📈 Next user to be promoted: {next_user[1]} (ID: {next_user[0]})")
        else:
            print("❌ No users available for promotion")
    
    # Perform the deletion in database directly (simulating the app logic)
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if this is the last admin
        c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
        admin_count = c.fetchone()[0]
        
        if admin_count <= 1:
            # Find next user to promote
            c.execute('SELECT id FROM users WHERE id != ? AND role != "admin" ORDER BY id LIMIT 1', (admin_to_delete[0],))
            next_user = c.fetchone()
            
            if next_user:
                # Promote next user
                c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                         ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', next_user[0]))
                print(f"✅ Promoted user ID {next_user[0]} to admin")
        
        # Delete the admin user
        c.execute('DELETE FROM users WHERE id = ?', (admin_to_delete[0],))
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted admin user ID {admin_to_delete[0]}")
        
        # Check new state
        check_database_state()
        
    except Exception as e:
        print(f"❌ Error during simulation: {e}")

if __name__ == '__main__':
    print("🧪 Testing Manual User Credentials & Admin Deletion")
    print("=" * 60)
    
    # Check initial state
    check_database_state()
    
    # Test authentication
    test_authentication()
    
    # Test admin deletion logic
    simulate_admin_self_deletion()
    
    print("\n✅ Testing completed!")