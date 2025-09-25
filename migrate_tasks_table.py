#!/usr/bin/env python3

import sqlite3

def migrate_tasks_table():
    """Migrate tasks table to ensure proper structure"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        print("=== MIGRATING TASKS TABLE ===")
        
        # Check current structure
        c.execute("PRAGMA table_info(tasks)")
        columns = c.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current columns: {column_names}")
        
        # Add missing columns if they don't exist
        if 'owner_id' not in column_names:
            try:
                c.execute('ALTER TABLE tasks ADD COLUMN owner_id INTEGER')
                print("✅ Added owner_id column")
            except Exception as e:
                print(f"Note: owner_id column might already exist: {e}")
        
        if 'task_end_time' not in column_names:
            try:
                c.execute('ALTER TABLE tasks ADD COLUMN task_end_time TEXT')
                print("✅ Added task_end_time column")
            except Exception as e:
                print(f"Note: task_end_time column might already exist: {e}")
        
        # Fix column naming inconsistencies
        if 'end_time' in column_names and 'task_end_time' not in column_names:
            # Create new table with correct structure
            c.execute('''CREATE TABLE IF NOT EXISTS tasks_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                task_date TEXT NOT NULL,
                task_time TEXT,
                task_end_time TEXT,
                location TEXT,
                status TEXT DEFAULT 'Not completed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER,
                assigned_user_id INTEGER
            )''')
            
            # Copy existing data
            c.execute('INSERT INTO tasks_new SELECT id, title, description, task_date, task_time, end_time, location, status, created_at, owner_id, assigned_user_id FROM tasks')
            
            # Drop old table and rename new one
            c.execute('DROP TABLE tasks')
            c.execute('ALTER TABLE tasks_new RENAME TO tasks')
            print("✅ Fixed column naming from end_time to task_end_time")
        
        # Update default status values
        c.execute("UPDATE tasks SET status = 'Not completed' WHERE status = 'pending' OR status IS NULL")
        
        conn.commit()
        conn.close()
        
        print("✅ Tasks table migration completed!")
        
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == '__main__':
    migrate_tasks_table()