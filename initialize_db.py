import sqlite3

def initialize_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    # Create tasks table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        task_date TEXT NOT NULL,
        task_time TEXT,
        location TEXT,
        status TEXT NOT NULL DEFAULT 'Not completed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create clients table
    c.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        account_type TEXT,
        company_name TEXT,
        actions TEXT,
        created_date TEXT,
        UNIQUE(client_name)
    )
    ''')

    # Create invoices table
    c.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        product TEXT,
        quantity INTEGER,
        price REAL,
        gst REAL,
        total REAL,
        status TEXT,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()
