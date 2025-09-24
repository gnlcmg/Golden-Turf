#!/usr/bin/env python3
"""
Fix user ID succession - make sure IDs are 1, 2, 3, etc.
"""

import sqlite3

def fix_user_id_succession():
    """Ensure user IDs are successive (1, 2, 3, etc.)"""
    print("🔄 Fixing user ID succession...")
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Get all users ordered by ID
        c.execute('SELECT id, name, email, password, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        
        print(f"📊 Found {len(users)} users with IDs: {[user[0] for user in users]}")
        
        if len(users) <= 1:
            print("ℹ️  Only 0-1 users, no reorganization needed")
            return
        
        # Clear the table
        c.execute('DELETE FROM users')
        
        # Reinsert with successive IDs starting from 1
        for i, user in enumerate(users, start=1):
            c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (i, user[1], user[2], user[3], user[4], user[5]))
            print(f"➕ Reassigned: '{user[1]}' ({user[2]}) from ID {user[0]} to ID {i}")
        
        conn.commit()
        
        # Verify the fix
        c.execute('SELECT id, name, email, role FROM users ORDER BY id')
        fixed_users = c.fetchall()
        
        print("\n✅ Fixed Database State:")
        for user in fixed_users:
            role_display = "ADMIN" if user[3] == 'admin' else "USER"
            print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {role_display}")
        
        print(f"\n🎯 User IDs are now successive: {[user[0] for user in fixed_users]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error fixing user IDs: {e}")

if __name__ == '__main__':
    fix_user_id_succession()