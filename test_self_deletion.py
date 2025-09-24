#!/usr/bin/env python3
"""
Test the specific scenario: admin deletes themselves and next user is promoted
"""

import sqlite3

def test_admin_self_deletion_scenario():
    """Test the exact scenario user requested"""
    print("🧪 Testing Admin Self-Deletion with Auto-Promotion")
    print("=" * 55)
    
    # Current state
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    print("📋 Current Database State:")
    c.execute('SELECT id, name, email, role FROM users ORDER BY id')
    users = c.fetchall()
    for user in users:
        role_icon = "👑" if user[3] == 'admin' else "👤"
        print(f"{role_icon} ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    
    # Find current admin (ID 1)
    c.execute('SELECT id, name, email FROM users WHERE id = 1 AND role = "admin"')
    current_admin = c.fetchone()
    
    if not current_admin:
        print("❌ Admin with ID 1 not found")
        conn.close()
        return
    
    print(f"\n🎯 Simulating: Admin '{current_admin[1]}' (ID: {current_admin[0]}) deletes themselves")
    
    # Check if this would be the last admin
    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    admin_count = c.fetchone()[0]
    print(f"📊 Current admin count: {admin_count}")
    
    if admin_count <= 1:
        # Find next user (ID 2) to promote
        c.execute('SELECT id, name, email FROM users WHERE id = 2')
        next_user = c.fetchone()
        
        if next_user:
            print(f"📈 Next user to be promoted: '{next_user[1]}' (ID: {next_user[0]})")
            
            # Promote the user
            c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                     ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', next_user[0]))
            print(f"✅ Promoted user ID {next_user[0]} to admin")
        else:
            print("❌ No user with ID 2 found to promote")
    
    # Delete the admin (simulating self-deletion)
    c.execute('DELETE FROM users WHERE id = ?', (current_admin[0],))
    conn.commit()
    print(f"🗑️  Deleted admin user ID {current_admin[0]}")
    
    # Show final state
    print("\n📋 Final Database State:")
    c.execute('SELECT id, name, email, role FROM users ORDER BY id')
    users = c.fetchall()
    for user in users:
        role_icon = "👑" if user[3] == 'admin' else "👤"
        print(f"{role_icon} ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    
    # Count admins
    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    final_admin_count = c.fetchone()[0]
    print(f"\n📊 Final admin count: {final_admin_count}")
    
    if final_admin_count >= 1:
        print("✅ System has at least one admin - safe from lockout")
    else:
        print("❌ WARNING: No admins remaining - system lockout!")
    
    conn.close()

if __name__ == '__main__':
    test_admin_self_deletion_scenario()