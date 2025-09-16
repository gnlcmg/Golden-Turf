import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT name, email, role FROM users")
users = c.fetchall()
conn.close()

print("All users:")
for user in users:
    print(f"Name: {user[0]}, Email: {user[1]}, Role: {user[2]}")

print("\nAdmin users:")
admins = [user for user in users if user[2] == 'admin']
for admin in admins:
    print(f"Name: {admin[0]}, Email: {admin[1]}")
 