import sqlite3

def add_created_date_column():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    try:
        c.execute("ALTER TABLE invoices ADD COLUMN created_date TEXT DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
        print("Column 'created_date' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_created_date_column()
