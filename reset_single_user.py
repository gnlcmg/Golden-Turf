#!/usr/bin/env python3
"""
Reset database to test scenario with user ID 1 as only user
"""

import sqlite3
import bcrypt

def reset_to_single_user():
    """Reset database to have only user ID 1"""
    print("🔄 Resetting database to single user scenario...")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Clear all users
    c.execute('DELETE FROM users')
    
    # Add only user ID 1
    hashed_password = bcrypt.hashpw('test123'.encode('utf-8'), bcrypt.gensalt())
    c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                 VALUES (1, 'Test User ID1', 'user1@test.com', ?, 'user', 'dashboard')''', 
              (hashed_password,))
    
    conn.commit()
    
    # Check current state
    c.execute('SELECT id, name, email, role FROM users')
    users = c.fetchall()
    
    print("📋 Reset Database State:")
    for user in users:
        role_icon = "👑" if user[3] == 'admin' else "👤"
        print(f"{role_icon} ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    
    conn.close()
    print("✅ Database reset completed!")

if __name__ == '__main__':
    reset_to_single_user()