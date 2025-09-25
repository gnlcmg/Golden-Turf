#!/usr/bin/env python3

import sqlite3

def check_tasks_table():
    """Check the structure and content of the tasks table"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check table structure
        print("=== TASKS TABLE STRUCTURE ===")
        c.execute("PRAGMA table_info(tasks)")
        columns = c.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}")
        
        # Check existing tasks
        print("\n=== EXISTING TASKS ===")
        c.execute("SELECT * FROM tasks ORDER BY id")
        tasks = c.fetchall()
        print(f"Total tasks: {len(tasks)}")
        for task in tasks:
            print(f"Task ID {task[0]}: {task[1]} - {task[3]} {task[4]}")
        
        # Test manual insert
        print("\n=== TESTING MANUAL INSERT ===")
        try:
            c.execute("""INSERT INTO tasks 
                         (title, description, task_date, task_time, end_time, location, status, assigned_user_id) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     ('Test Task', 'Test Description', '2024-12-25', '10:00', '11:00', 'Test Location', 'pending', 1))
            conn.commit()
            print("✅ Manual insert successful!")
        except Exception as e:
            print(f"❌ Manual insert failed: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    check_tasks_table()