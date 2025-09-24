#!/usr/bin/env python3
"""
Test the updated admin management system
"""

import sqlite3

def check_current_system():
    """Check the current state after optimization"""
    print("🧪 Testing Optimized Admin Management System")
    print("=" * 50)
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check current state
    c.execute('SELECT id, name, email, role FROM users ORDER BY id')
    users = c.fetchall()
    
    print("📋 Current Database State:")
    total_users = len(users)
    admin_count = sum(1 for user in users if user[3] == 'admin')
    
    for user in users:
        role_icon = "👑" if user[3] == 'admin' else "👤"
        print(f"{role_icon} ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}")
    
    print(f"\n📊 Summary: {total_users} total users, {admin_count} admin(s)")
    
    # Test the single user scenario
    if total_users == 1:
        print("\n🎯 Single User Scenario:")
        user = users[0]
        if user[0] == 1 and user[3] == 'admin':
            print("✅ User ID 1 is correctly the only admin when alone")
        else:
            print("❌ User ID 1 should be admin when they're the only user")
    
    # Test admin constraints
    if total_users > 1:
        print(f"\n🔒 Admin Management:")
        if admin_count >= 1:
            print("✅ System has at least one admin")
        else:
            print("❌ WARNING: No admins found - system issue!")
    
    conn.close()
    print("\n✅ System check completed!")

if __name__ == '__main__':
    check_current_system()