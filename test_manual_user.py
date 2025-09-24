#!/usr/bin/env python3
"""
Test script to add manual users with plain text passwords
This simulates manually added users to test the authentication system
"""

import sqlite3

def add_test_users():
    """Add test users with plain text passwords"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Test users with plain text passwords
        test_users = [
            ('Test User 1', 'test1@example.com', 'password123', 'user', 'dashboard'),
            ('Test User 2', 'test2@example.com', 'mypassword', 'user', 'dashboard'),
            ('Manual Admin', 'admin@test.com', 'admin123', 'admin', 'dashboard,payments,clients,calendar,products,profiles')
        ]
        
        for name, email, password, role, permissions in test_users:
            try:
                # Check if user already exists
                c.execute('SELECT id FROM users WHERE email = ?', (email,))
                if c.fetchone():
                    print(f"⚠️  User {email} already exists, skipping...")
                    continue
                
                # Insert user with plain text password
                c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                         (name, email, password, role, permissions))
                print(f"✅ Added user: {name} ({email}) with plain text password")
                
            except sqlite3.IntegrityError as e:
                print(f"❌ Error adding {email}: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n📋 Current users in database:")
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, email, role, password FROM users')
        users = c.fetchall()
        for user in users:
            password = user[4]
            if isinstance(password, bytes):
                password = password.decode('utf-8')
            password_type = "bcrypt" if password.startswith('$2b$') else "plain text"
            print(f"  ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}, Password: {password_type}")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    print("🔧 Adding test users with manual credentials...")
    add_test_users()
    print("\n✅ Test users added successfully!")
    print("💡 Try logging in with:")
    print("   - test1@example.com / password123")
    print("   - test2@example.com / mypassword") 
    print("   - admin@test.com / admin123")