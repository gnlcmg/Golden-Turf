import sqlite3

def read_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Check tables
    c.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = c.fetchall()
    print('Tables in database:', tables)
    
    # Read from users table
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    print('Users in database:', users)
    
    # Read from tasks table if it exists
    try:
        c.execute('SELECT * FROM tasks')
        tasks = c.fetchall()
        print('Tasks in database:', tasks)
    except sqlite3.Error as e:
        print('Error reading tasks table:', e)
    
    conn.close()

if __name__ == "__main__":
    read_database()
