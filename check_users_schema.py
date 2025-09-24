import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

print("Users table schema:")
c.execute('PRAGMA table_info(users)')
columns = c.fetchall()

for col in columns:
    col_name = col[1]
    col_type = col[2]
    not_null = "NOT NULL" if col[3] else "NULL"
    default_val = f"DEFAULT: {col[4]}" if col[4] else ""
    print(f"  {col_name} {col_type} {not_null} {default_val}")

conn.close()