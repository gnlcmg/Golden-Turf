import sqlite3

# Connect to the database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check if invoices table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
exists = cursor.fetchone()
print(f"Invoices table exists: {bool(exists)}")

if exists:
    # Get table structure
    cursor.execute("PRAGMA table_info(invoices)")
    columns = cursor.fetchall()
    print("\nInvoices table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
else:
    print("Invoices table does not exist!")

conn.close()