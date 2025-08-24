import sqlite3

def check_database_structure():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check all tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check invoices table structure
        print("\nChecking invoices table structure:")
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        invoices_exists = c.fetchone()
        
        if invoices_exists:
            print("invoices table exists")
            c.execute("PRAGMA table_info(invoices)")
            columns = c.fetchall()
            print("Columns in invoices table:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        else:
            print("invoices table does not exist")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database_structure()
