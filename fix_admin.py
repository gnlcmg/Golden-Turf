import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Update user ID 1 to admin with full permissions
c.execute('''UPDATE users 
             SET role = ?, permissions = ? 
             WHERE id = ?''', 
          ('admin', 'dashboard,payments,clients,calendar,products', 1))

conn.commit()
print("User ID 1 has been updated to admin with full permissions")

# Verify the change
c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = 1')
user = c.fetchone()
print(f'Updated user: ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}, Permissions: {user[4]}')

conn.close()