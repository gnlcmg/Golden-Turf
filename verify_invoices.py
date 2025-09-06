import sqlite3

def verify_invoices_structure():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if invoices table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        invoices_exists = c.fetchone()
        
        if invoices_exists:
            print("✓ invoices table exists")
            
            # Get column information
            c.execute("PRAGMA table_info(invoices)")
            columns = c.fetchall()
            
            print("\nCurrent columns in invoices table:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
                
            # Check for expected columns
            expected_columns = ['id', 'client_id', 'product', 'quantity', 'price', 'gst', 'total', 'status', 'created_date']
            current_columns = [col[1] for col in columns]
            
            print(f"\nExpected columns: {expected_columns}")
            print(f"Current columns: {current_columns}")
            
            if set(expected_columns) == set(current_columns):
                print("✓ Invoices table structure matches expected original structure")
            else:
                print("✗ Invoices table structure does not match expected original structure")
                
        else:
            print("✗ invoices table does not exist")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_invoices_structure()
