import sqlite3

def verify_products():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if products table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        products_exists = c.fetchone()
        
        if products_exists:
            print("✓ products table exists")
            
            # Get column information
            c.execute("PRAGMA table_info(products)")
            columns = c.fetchall()
            
            print("\nColumns in products table:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
                
            # Get sample data
            c.execute("SELECT * FROM products LIMIT 5")
            sample_data = c.fetchall()
            
            print(f"\nSample data (first 5 rows):")
            for row in sample_data:
                print(f"  {row}")
                
        else:
            print("✗ products table does not exist")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_products()
