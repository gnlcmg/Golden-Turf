import sqlite3

def undo_invoices_changes():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Backup current invoices table
        c.execute('''
            CREATE TABLE IF NOT EXISTS invoices_backup AS SELECT * FROM invoices
        ''')
        
        # Drop the current invoices table
        c.execute("DROP TABLE IF EXISTS invoices")
        
        # Recreate the invoices table with the original structure
        c.execute('''
            CREATE TABLE invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                product TEXT,
                quantity INTEGER,
                price REAL,
                gst REAL,
                total REAL,
                status TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        print("Invoices table has been restored to its original structure.")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    undo_invoices_changes()
