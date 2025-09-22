import sqlite3

# Test the auto-admin logic
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Check current user count
c.execute('SELECT COUNT(*) FROM users')
user_count = c.fetchone()[0]
print(f"Current user count: {user_count}")

# Simulate what the registration logic does
if user_count == 0:
    role = 'admin'
    permissions = 'dashboard,payments,clients,calendar,products'
    print("Would create admin user (first user)")
else:
    role = 'user'
    permissions = ''
    print("Would create regular user")

print(f"Role: {role}, Permissions: {permissions}")

conn.close()