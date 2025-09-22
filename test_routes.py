from app import app
import sqlite3

with app.test_request_context():
    from flask import url_for
    
    # Test URL generation
    print("Testing URL generation:")
    try:
        delete_url = url_for('delete_user', user_id=1)
        print(f"Delete URL: {delete_url}")
    except Exception as e:
        print(f"Error generating delete URL: {e}")
    
    try:
        edit_url = url_for('edit_user', user_id=1)
        print(f"Edit URL: {edit_url}")
    except Exception as e:
        print(f"Error generating edit URL: {e}")
    
    # Check if users exist
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name, email, role FROM users')
    users = c.fetchall()
    print(f"\nUsers in database: {len(users)}")
    for user in users:
        print(f"  ID: {user[0]}, Name: {user[1]}, Role: {user[3]}")
    conn.close()