import sqlite3

def test_id_reset():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    print("=== Testing ID Reset Functionality ===")
    
    # Check current clients
    c.execute('SELECT id, client_name FROM clients ORDER BY id')
    clients = c.fetchall()
    print(f"\nCurrent clients: {len(clients)}")
    for client in clients:
        print(f"  ID {client[0]}: {client[1]}")
    
    # Check current invoices  
    c.execute('SELECT id, client_name FROM invoices ORDER BY id')
    invoices = c.fetchall()
    print(f"\nCurrent invoices: {len(invoices)}")
    for invoice in invoices:
        print(f"  ID {invoice[0]}: {invoice[1]}")
    
    # Check sequence values
    c.execute('SELECT name, seq FROM sqlite_sequence WHERE name IN ("clients", "invoices")')
    sequences = c.fetchall()
    print(f"\nCurrent sequences:")
    for seq in sequences:
        print(f"  {seq[0]}: next ID will be {seq[1] + 1}")
    
    conn.close()

if __name__ == "__main__":
    test_id_reset()