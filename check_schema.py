import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
print("Columns:", [col[1] for col in columns])
c.execute("SELECT id, name, email, role FROM users")
users = c.fetchall()
print("Users:", users)
conn.close()
