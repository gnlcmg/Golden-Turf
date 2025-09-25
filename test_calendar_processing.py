#!/usr/bin/env python3

import sqlite3
from datetime import datetime
import sys
sys.path.append('.')

def db_exec(query, params=(), fetch=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(query, params)
    if fetch == 'one': result = c.fetchone()
    elif fetch == 'all': result = c.fetchall()
    else: result = None
    conn.commit()
    conn.close()
    return result

def test_calendar_task_processing():
    """Test how tasks are processed for calendar display"""
    try:
        print("=== TESTING CALENDAR TASK PROCESSING ===")
        
        # Get all tasks for owner_id = 1 (simulating session user)
        tasks = db_exec('SELECT * FROM tasks WHERE owner_id = ? ORDER BY task_date, task_time', (1,), 'all') or []
        print(f"Retrieved {len(tasks)} tasks")
        
        # Process tasks by date (same logic as calendar route)
        tasks_by_date = {}
        for task in tasks:
            if task[3]:  # task_date (index 3)
                print(f"Processing task: ID={task[0]}, Title={task[1]}, Date={task[3]}")
                try:
                    task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
                    if task_date not in tasks_by_date:
                        tasks_by_date[task_date] = []
                    tasks_by_date[task_date].append(task)
                    print(f"  → Added to date {task_date}")
                except ValueError as e:
                    print(f"  → Date parsing error: {e}")
        
        print(f"\nTasks organized by date:")
        for date, task_list in sorted(tasks_by_date.items()):
            print(f"  {date}: {len(task_list)} tasks")
            for task in task_list:
                print(f"    - {task[1]} at {task[4] if task[4] else 'no time'}")
        
        # Check specifically for today's date
        today = datetime.now().date()
        print(f"\nTasks for today ({today}):")
        today_tasks = tasks_by_date.get(today, [])
        print(f"Found {len(today_tasks)} tasks for today")
        for task in today_tasks:
            print(f"  - {task[1]} at {task[4] if task[4] else 'no time'}")
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_calendar_task_processing()