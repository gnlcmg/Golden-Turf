#!/usr/bin/env python3
"""
Remove image columns from products table
"""

import sqlite3

def remove_image_columns():
    """Remove image_url and image_urls columns from products table"""
    print("🗑️  Removing image columns from products table...")
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check current products table data
        c.execute('SELECT COUNT(*) FROM products')
        product_count = c.fetchone()[0]
        print(f"📊 Found {product_count} products in table")
        
        if product_count > 0:
            # Show current products with images
            c.execute('SELECT id, product_name, image_url, image_urls FROM products')
            products = c.fetchall()
            print("📋 Current products with image data:")
            for prod in products:
                print(f"  ID: {prod[0]}, Name: {prod[1]}")
                print(f"    image_url: {prod[2] or 'NULL'}")
                print(f"    image_urls: {prod[3] or 'NULL'}")
        
        # Create new table without image columns
        print("\n🔧 Creating new products table without image columns...")
        c.execute('''CREATE TABLE products_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            turf_type TEXT,
            description TEXT,
            stock INTEGER DEFAULT 0,
            price REAL DEFAULT 0.0
        )''')
        
        # Copy data without image columns
        if product_count > 0:
            c.execute('''INSERT INTO products_new (id, product_name, turf_type, description, stock, price)
                         SELECT id, product_name, turf_type, description, stock, price FROM products''')
            print(f"✅ Copied {product_count} products without image data")
        
        # Drop old table and rename new one
        c.execute('DROP TABLE products')
        c.execute('ALTER TABLE products_new RENAME TO products')
        
        conn.commit()
        
        # Verify the change
        print("\n🔍 Verifying new table structure:")
        c.execute('PRAGMA table_info(products)')
        columns = c.fetchall()
        
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        print("✅ Successfully removed image columns from products table!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error removing image columns: {e}")

if __name__ == '__main__':
    remove_image_columns()