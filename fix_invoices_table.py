import sqlite3

def fix_invoices_table():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # First, check if the invoices table exists and has the discount column
        c.execute("PRAGMA table_info(invoices)")
        columns = c.fetchall()
        column_names = [col[1] for col in columns]
        
        print("Current columns in invoices table:", column_names)
        
        # If discount column exists, we need to recreate the table
        if 'discount' in column_names and 'due_date' not in column_names:
            print("Recreating invoices table with correct schema...")
            
            # Create a temporary table with the correct schema
            c.execute('''
                CREATE TABLE invoices_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    product TEXT,
                    quantity INTEGER,
                    price REAL,
                    gst REAL,
                    total REAL,
                    due_date TEXT,
                    status TEXT,
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            ''')
            
            # Drop the old invoices table
            c.execute("DROP TABLE invoices")
            
            # Rename the temporary table to invoices
            c.execute("ALTER TABLE invoices_temp RENAME TO invoices")
            
            print("Invoices table recreated successfully with due_date column and without discount column")
            
        elif 'due_date' in column_names:
            print("due_date column already exists in invoices table")
        else:
            print("Unknown table structure")
            
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_invoices_table()
