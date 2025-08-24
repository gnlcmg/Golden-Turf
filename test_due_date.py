import sqlite3

def test_due_date_query():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Try to query the due_date column
        c.execute("SELECT due_date FROM invoices LIMIT 1")
        result = c.fetchone()
        print("Success: due_date column exists and can be queried")
        print(f"Result: {result}")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        if "no such column" in str(e):
            print(f"Error: {e}")
            print("The due_date column does not exist in the invoices table")
        else:
            print(f"Other operational error: {e}")
            
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_due_date_query()
