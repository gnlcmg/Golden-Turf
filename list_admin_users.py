#!/usr/bin/env python3
"""
Admin Users Listing Script
==========================
Purpose: Lists all admin users with their names and emails from the Golden Turf database
Usage: python list_admin_users.py
"""

import sqlite3
import os
from datetime import datetime

def list_admin_users():
    """List all admin users with their details"""
    db_path = 'users.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file 'users.db' not found!")
        print(f"   Make sure you're running this from the correct directory: {os.getcwd()}")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query admin users
        cursor.execute('''
            SELECT id, name, email, role, permissions 
            FROM users 
            WHERE role = ? 
            ORDER BY id
        ''', ('admin',))
        
        admins = cursor.fetchall()
        
        # Display results
        print("=" * 80)
        print("🔑 GOLDEN TURF - ADMIN USERS LIST")
        print("=" * 80)
        print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total Admin Users: {len(admins)}")
        print("=" * 80)
        
        if admins:
            print(f"{'ID':<4} | {'NAME':<25} | {'EMAIL':<35} | {'PERMISSIONS'}")
            print("-" * 80)
            
            for admin in admins:
                admin_id = admin[0]
                name = admin[1] or 'N/A'
                email = admin[2] or 'N/A'
                permissions = admin[4] or 'basic'
                
                # Truncate long fields for better display
                name_display = name[:24] if len(name) > 24 else name
                email_display = email[:34] if len(email) > 34 else email
                perms_display = permissions.replace(',', ', ')[:30] if len(permissions) > 30 else permissions.replace(',', ', ')
                
                print(f"{admin_id:<4} | {name_display:<25} | {email_display:<35} | {perms_display}")
                
        else:
            print("⚠️  No admin users found in the database!")
            print("   This might indicate a setup issue.")
        
        print("=" * 80)
        
        # Additional stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('user',))
        regular_users = cursor.fetchone()[0]
        
        print(f"📈 Database Statistics:")
        print(f"   • Total Users: {total_users}")
        print(f"   • Admin Users: {len(admins)}")
        print(f"   • Regular Users: {regular_users}")
        print("=" * 80)
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    list_admin_users()