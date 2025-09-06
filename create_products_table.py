mport sqlite3

def create_products_table():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Create products table
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                turf_type TEXT NOT NULL,
                description TEXT,
                stock INTEGER NOT NULL
            )
        ''')
        
        # Insert sample data
        sample_products = [
            ('Golden Imperial Lush', 'Synthetic Turf', 'Premium synthetic turf designed for a lush, natural look.', 100),
            ('Golden Green Lush', 'Synthetic Turf', 'Artificial grass with vibrant green color, ideal for backyards.', 150),
            ('Golden Natural 40mm', 'Synthetic Turf', 'Realistic 40mm pile height turf, perfect for residential lawns.', 200),
            ('Golden Golf Turf', 'Synthetic Turf', 'Specially crafted for golf putting and chipping.', 50),
            ('Golden Premium Turf', 'Synthetic Turf', 'High-grade synthetic grass for premium landscaping projects.', 75),
            ('Peg (U-pins/Nails)', 'Accessory', 'Used for securing turf', 500),
            ('Fountains', 'Accessory', 'Decorative fountains', 20),
            ('Artificial Hedges', 'Accessory', 'Hedges for decoration', 200),
            ('Black Pebbles', 'Pebbles', '20kg bag of black pebbles', 150),
            ('White Pebbles', 'Pebbles', '20kg bag of white pebbles', 150),
            ('Bamboo Products', 'Accessory', 'Various sizes of bamboo', 100),
            ('Adhesive Joining Tape', 'Accessory', 'Tape for joining turf', 300)
        ]
        
        c.executemany('INSERT INTO products (product_name, turf_type, description, stock) VALUES (?, ?, ?, ?)', sample_products)
        
        conn.commit()
        print("Products table created and sample data inserted successfully.")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_products_table()
