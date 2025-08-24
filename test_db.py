import sqlite3
import os

def test_database():
    print("Testing database connection...")
    
    # Check if database file exists
    if not os.path.exists('users.db'):
        print("ERROR: users.db file does not exist!")
        return False
    
    print("✓ users.db file exists")
    
    try:
        # Connect to database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        print("✓ Connected to database successfully")
        
        # Check tables
        c.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = c.fetchall()
        print(f"✓ Tables in database: {tables}")
        
        # Check tasks table specifically
        c.execute('PRAGMA table_info(tasks)')
        task_columns = c.fetchall()
        print(f"✓ Tasks table columns: {task_columns}")
        
        # Check if there are any tasks
        c.execute('SELECT COUNT(*) FROM tasks')
        task_count = c.fetchone()[0]
        print(f"✓ Number of tasks in database: {task_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_database()
