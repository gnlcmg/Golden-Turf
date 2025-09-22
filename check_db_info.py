import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Check the sqlite_sequence table to see auto-increment values
try:
    c.execute("SELECT * FROM sqlite_sequence WHERE name='users'")
    sequence = c.fetchone()
    if sequence:
        print(f"Current auto-increment value for users table: {sequence[1]}")
    else:
        print("No sequence found for users table")
except sqlite3.OperationalError as e:
    print(f"Error checking sequence: {e}")

# Check table schema
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
print("\nUsers table schema:")
for col in columns:
    print(f"Column: {col[1]}, Type: {col[2]}, Primary Key: {col[5]}")

conn.close()