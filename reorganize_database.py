#!/usr/bin/env python3
"""
Reorganize database with successive user IDs and set mahi.gohil3695@gmail.com as ID 1
"""

import sqlite3
import bcrypt

def reorganize_database():
    """Reset user IDs to be successive and make mahi.gohil3695@gmail.com ID 1"""
    print("🔄 Reorganizing database with successive IDs...")
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Get all current users
        c.execute('SELECT id, name, email, password, role, permissions FROM users ORDER BY id')
        current_users = c.fetchall()
        
        if not current_users:
            print("ℹ️  No users found in database")
            
            # Create mahi.gohil3695@gmail.com as the first user (ID 1)
            print("📝 Creating mahi.gohil3695@gmail.com as user ID 1...")
            hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
            c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                         VALUES (1, 'Mahi', ?, ?, 'admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles')''', 
                      (hashed_password, 'mahi.gohil3695@gmail.com'))
            conn.commit()
            print("✅ Created mahi.gohil3695@gmail.com as admin user ID 1")
            
        else:
            print(f"📊 Found {len(current_users)} existing users")
            
            # Clear the users table
            c.execute('DELETE FROM users')
            
            # Find mahi.gohil3695@gmail.com and put them as ID 1
            mahi_user = None
            other_users = []
            
            for user in current_users:
                if user[2] == 'mahi.gohil3695@gmail.com':  # email field
                    mahi_user = user
                else:
                    other_users.append(user)
            
            # Insert mahi as ID 1 (admin)
            if mahi_user:
                print("👑 Setting mahi.gohil3695@gmail.com as admin user ID 1...")
                c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                             VALUES (1, ?, ?, ?, 'admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles')''', 
                          (mahi_user[1], mahi_user[2], mahi_user[3]))
            else:
                # Create mahi user if they don't exist
                print("📝 Creating mahi.gohil3695@gmail.com as new admin user ID 1...")
                hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
                c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                             VALUES (1, 'Mahi', 'mahi.gohil3695@gmail.com', ?, 'admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles')''', 
                          (hashed_password,))
            
            # Insert other users with successive IDs (2, 3, 4, etc.)
            for i, user in enumerate(other_users, start=2):
                print(f"➕ Adding user '{user[1]}' as ID {i}...")
                c.execute('''INSERT INTO users (id, name, email, password, role, permissions) 
                             VALUES (?, ?, ?, ?, 'user', 'dashboard')''', 
                          (i, user[1], user[2], user[3]))
            
            conn.commit()
        
        # Display final state
        print("\n📋 Final Database State:")
        c.execute('SELECT id, name, email, role FROM users ORDER BY id')
        final_users = c.fetchall()
        
        for user in final_users:
            role_display = "ADMIN" if user[3] == 'admin' else "USER"
            print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {role_display}")
        
        print(f"\n✅ Database reorganized! Total users: {len(final_users)}")
        print("🎯 mahi.gohil3695@gmail.com is now user ID 1 and admin")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error reorganizing database: {e}")

if __name__ == '__main__':
    reorganize_database()