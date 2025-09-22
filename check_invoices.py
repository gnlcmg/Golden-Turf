import sqlite3

# Check the main database for invoices
conn = sqlite3.connect('users.db')
c = conn.cursor()

print("=== CHECKING INVOICES TABLE ===")
try:
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0]
    print(f"Total invoices in database: {count}")
    
    if count > 0:
        c.execute("SELECT id, status, total, created_date, owner_id FROM invoices ORDER BY created_date DESC")
        invoices = c.fetchall()
        print("\nInvoice details:")
        for inv in invoices:
            print(f"  ID: {inv[0]}, Status: {inv[1]}, Total: {inv[2]}, Date: {inv[3]}, Owner: {inv[4]}")
        
        # Calculate totals
        c.execute("SELECT SUM(total) FROM invoices WHERE status != 'Unpaid'")
        paid_total = c.fetchone()[0] or 0
        print(f"\nTotal of paid invoices: ${paid_total}")
        
        c.execute("SELECT SUM(total) FROM invoices")
        all_total = c.fetchone()[0] or 0
        print(f"Total of all invoices: ${all_total}")
        
except Exception as e:
    print(f"Error checking invoices: {e}")

print("\n=== CHECKING CLIENTS TABLE ===")
try:
    c.execute("SELECT COUNT(*) FROM clients")
    count = c.fetchone()[0]
    print(f"Total clients: {count}")
    
    if count > 0:
        c.execute("SELECT id, client_name FROM clients LIMIT 5")
        clients = c.fetchall()
        print("Sample clients:")
        for client in clients:
            print(f"  ID: {client[0]}, Name: {client[1]}")
            
except Exception as e:
    print(f"Error checking clients: {e}")

print("\n=== CHECKING USERS TABLE ===")
try:
    c.execute("SELECT id, name, role FROM users")
    users = c.fetchall()
    print("Users in system:")
    for user in users:
        print(f"  ID: {user[0]}, Name: {user[1]}, Role: {user[2]}")
        
except Exception as e:
    print(f"Error checking users: {e}")

conn.close()