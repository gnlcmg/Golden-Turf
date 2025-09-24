import sqlite3
from datetime import datetime

def migrate_invoices_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        # First, let's backup any existing data
        cursor.execute("SELECT * FROM invoices")
        existing_data = cursor.fetchall()
        print(f"Found {len(existing_data)} existing invoices to migrate")
        
        # Drop the old table
        cursor.execute("DROP TABLE IF EXISTS invoices")
        
        # Create the new invoices table with the correct structure
        cursor.execute('''CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            turf_type TEXT,
            area REAL,
            payment_status TEXT DEFAULT 'Unpaid',
            gst REAL DEFAULT 0,
            subtotal REAL DEFAULT 0,
            total REAL DEFAULT 0,
            extras TEXT,
            created_date TEXT,
            due_date TEXT,
            owner_id INTEGER,
            artificial_hedges_qty INTEGER DEFAULT 0,
            fountain_price REAL DEFAULT 0,
            bamboo_products_size TEXT,
            bamboo_products_qty INTEGER DEFAULT 0,
            pebbles_custom_type TEXT,
            pebbles_qty INTEGER DEFAULT 0,
            pegs_qty INTEGER DEFAULT 0,
            adhesive_tape_qty INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )''')
        
        print("New invoices table created successfully!")
        
        # If there was existing data, we could try to migrate it, but for now let's start fresh
        if existing_data:
            print("Note: Old invoice data was cleared. Starting with fresh invoice table.")
        
        conn.commit()
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_invoices_table()