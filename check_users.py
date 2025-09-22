import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('SELECT id, name, email, role, permissions FROM users')
users = c.fetchall()

print('Users in database:')
for row in users:
    print(f'ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Role: {row[3]}, Permissions: {row[4]}')

print(f'\nTotal users: {len(users)}')
conn.close()