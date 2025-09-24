#!/usr/bin/env python3
"""
Create a test user to demonstrate permission editing
"""

import sqlite3
import bcrypt

def create_test_user():
    """Create a test user with limited permissions"""
    print("➕ Creating test user for permission editing...")
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Create a test user with limited permissions
        hashed_password = bcrypt.hashpw('test123'.encode('utf-8'), bcrypt.gensalt())
        c.execute('''INSERT INTO users (name, email, password, role, permissions) 
                     VALUES (?, ?, ?, ?, ?)''', 
                  ('Test User', 'testuser@example.com', hashed_password, 'user', 'dashboard,products_list'))
        
        conn.commit()
        
        # Show current users
        c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        
        print("📋 Current Users:")
        for user in users:
            print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
            print(f"    Permissions: {user[4]}")
        
        conn.close()
        print("✅ Test user created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")

if __name__ == '__main__':
    create_test_user()