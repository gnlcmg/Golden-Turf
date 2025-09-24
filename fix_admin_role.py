import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Get the first user (should be admin)
c.execute('SELECT id, name, email FROM users ORDER BY id LIMIT 1')
first_user = c.fetchone()

if first_user:
    user_id = first_user[0]
    print(f"Setting user ID {user_id} ({first_user[1]}) as admin...")
    
    # Update role and permissions
    c.execute("UPDATE users SET role = ?, permissions = ? WHERE id = ?", 
              ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', user_id))
    
    conn.commit()
    print("Admin role updated successfully!")
    
    # Verify the change
    c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = ?', (user_id,))
    updated_user = c.fetchone()
    print(f"Verified - ID: {updated_user[0]}, Name: {updated_user[1]}, Role: {updated_user[3]}, Permissions: {updated_user[4]}")
else:
    print("No users found!")

conn.close()