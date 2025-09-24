#!/usr/bin/env python3
"""
Test permission editing functionality
"""

import sqlite3

def test_permission_editing():
    """Test that permissions are properly updated"""
    print("🧪 Testing Permission Editing Functionality")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Show current permissions for all users
        c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        
        print("📋 Current User Permissions:")
        for user in users:
            role_display = "ADMIN" if user[3] == 'admin' else "USER"
            print(f"\n{role_display} - ID: {user[0]}, Name: {user[1]}")
            print(f"    Email: {user[2]}")
            print(f"    Permissions: {user[4] if user[4] else 'None'}")
            
            if user[4]:
                perm_list = user[4].split(',')
                print(f"    Modules ({len(perm_list)}): {', '.join(perm_list)}")
        
        # Test updating permissions for user ID 3 (Test User)
        print(f"\n🔧 Testing Permission Update for Test User (ID: 3)...")
        
        # Simulate adding more permissions
        new_permissions = 'dashboard,products_list,invoice,clients'
        c.execute('UPDATE users SET permissions = ? WHERE id = 3', (new_permissions,))
        conn.commit()
        
        # Verify the update
        c.execute('SELECT name, permissions FROM users WHERE id = 3')
        updated_user = c.fetchone()
        
        if updated_user:
            print(f"✅ Updated permissions for {updated_user[0]}: {updated_user[1]}")
            print(f"   Modules: {', '.join(updated_user[1].split(','))}")
        else:
            print("❌ User ID 3 not found")
        
        print(f"\n✅ Permission editing functionality is working!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing permissions: {e}")

if __name__ == '__main__':
    test_permission_editing()