import sqlite3

# Check ID 1 user permissions
conn = sqlite3.connect('users.db')
c = conn.cursor()

result = c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = 1').fetchone()
if result:
    print(f"ID 1 User Details:")
    print(f"ID: {result[0]}")
    print(f"Name: {result[1]}")
    print(f"Email: {result[2]}")
    print(f"Role: {result[3]}")
    print(f"Permissions: {result[4]}")
else:
    print("No user with ID 1 found")

# Check all users
all_users = c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id').fetchall()
print(f"\nAll users in database:")
for user in all_users:
    print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Role: {user[3]}, Permissions: {user[4]}")

conn.close()