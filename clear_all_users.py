#!/usr/bin/env python3
"""
Remove all users from the database
"""

import sqlite3

def remove_all_users():
    """Clear all users from the database"""
    print("🗑️  Removing all users from database...")
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check current users before deletion
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        print(f"📊 Current user count: {user_count}")
        
        if user_count > 0:
            # Remove all users
            c.execute('DELETE FROM users')
            conn.commit()
            
            # Verify deletion
            c.execute('SELECT COUNT(*) FROM users')
            remaining_count = c.fetchone()[0]
            
            print(f"✅ Deleted all users. Remaining count: {remaining_count}")
        else:
            print("ℹ️  No users found in database")
        
        conn.close()
        print("🎯 Database cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error removing users: {e}")

if __name__ == '__main__':
    remove_all_users()