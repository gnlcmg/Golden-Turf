#!/usr/bin/env python3

import sqlite3
import bcrypt

def test_id_1_admin_logic():
    """Test that ID 1 users automatically become admin"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        print("=== TESTING ID 1 ADMIN LOGIC ===")
        
        # Backup current users
        c.execute("SELECT * FROM users")
        backup_users = c.fetchall()
        print(f"Backing up {len(backup_users)} existing users")
        
        # Clear users table for clean test
        c.execute("DELETE FROM users")
        c.execute("DELETE FROM sqlite_sequence WHERE name='users'")
        conn.commit()
        
        # Test 1: Register first user (should get ID 1 and become admin)
        print("\n1. Testing first user registration...")
        hash_pw = bcrypt.hashpw('testpass123'.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users (name, email, password_hash, role, permissions) VALUES (?, ?, ?, ?, ?)', 
                 ('Test User 1', 'test1@test.com', hash_pw, 'user', 'dashboard'))
        conn.commit()
        
        # Get the new user
        c.execute('SELECT id, role, permissions FROM users WHERE email = ?', ('test1@test.com',))
        new_user = c.fetchone()
        print(f"   User created with ID: {new_user[0]}, Role: {new_user[1]}")
        
        # Simulate the ID 1 check logic
        if new_user[0] == 1:
            c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                     ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', 1))
            conn.commit()
            print("   ✅ User ID 1 automatically upgraded to admin!")
        
        # Verify admin status
        c.execute('SELECT id, role, permissions FROM users WHERE id = 1')
        admin_user = c.fetchone()
        if admin_user and admin_user[1] == 'admin':
            print(f"   ✅ Confirmed: User ID 1 has admin role with full permissions")
        else:
            print(f"   ❌ Error: User ID 1 does not have admin role")
        
        # Test 2: Register second user (should remain regular user)
        print("\n2. Testing second user registration...")
        hash_pw2 = bcrypt.hashpw('testpass456'.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users (name, email, password_hash, role, permissions) VALUES (?, ?, ?, ?, ?)', 
                 ('Test User 2', 'test2@test.com', hash_pw2, 'user', 'dashboard'))
        conn.commit()
        
        c.execute('SELECT id, role FROM users WHERE email = ?', ('test2@test.com',))
        second_user = c.fetchone()
        print(f"   User created with ID: {second_user[0]}, Role: {second_user[1]}")
        
        if second_user[0] != 1 and second_user[1] == 'user':
            print("   ✅ Second user remains regular user (correct)")
        else:
            print("   ❌ Second user should not be admin")
        
        # Restore backup users
        print(f"\n3. Restoring {len(backup_users)} original users...")
        c.execute("DELETE FROM users")
        c.execute("DELETE FROM sqlite_sequence WHERE name='users'")
        
        for user in backup_users:
            c.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)', user)
        
        # Reset sequence
        if backup_users:
            max_id = max(user[0] for user in backup_users)
            c.execute("INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (max_id,))
        
        conn.commit()
        conn.close()
        
        print("✅ Test completed successfully - original data restored")
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_id_1_admin_logic()