import sqlite3

def check_invoices_schema():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if invoices table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        table_exists = c.fetchone()
        
        if table_exists:
            print("invoices table exists")
            
            # Get all columns in invoices table
            c.execute("PRAGMA table_info(invoices)")
            columns = c.fetchall()
            
            print("Columns in invoices table:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
                
            # Check if due_date column exists
            due_date_exists = any(col[1] == 'due_date' for col in columns)
            print(f"due_date column exists: {due_date_exists}")
            
        else:
            print("invoices table does not exist")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_invoices_schema()
