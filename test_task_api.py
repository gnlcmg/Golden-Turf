#!/usr/bin/env python3

import sqlite3

def test_task_api_data():
    """Test the data structure for task API"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        print("=== TESTING TASK API DATA STRUCTURE ===")
        
        # Get a task to understand the column structure
        c.execute("SELECT * FROM tasks LIMIT 1")
        task = c.fetchone()
        
        if task:
            print(f"Task columns ({len(task)} total):")
            for i, value in enumerate(task):
                print(f"  Index {i}: {value}")
            
            # Expected structure based on our schema:
            # 0: id, 1: title, 2: description, 3: task_date, 4: task_time, 
            # 5: location, 6: status, 7: created_at, 8: task_end_time, 
            # 9: owner_id, 10: assigned_user_id
            
            print(f"\nProposed API response structure:")
            print(f"  id: {task[0]}")
            print(f"  title: {task[1]}")
            print(f"  description: {task[2]}")
            print(f"  date: {task[3]}")
            print(f"  time: {task[4]}")
            print(f"  end_time: {task[8]}")  # task_end_time
            print(f"  location: {task[5]}")
            print(f"  status: {task[6]}")
            print(f"  created_at: {task[7]}")
            print(f"  assigned_user_id: {task[10] if len(task) > 10 else None}")
        else:
            print("No tasks found in database")
        
        conn.close()
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_task_api_data()