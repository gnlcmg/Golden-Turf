#!/usr/bin/env python3

import sqlite3
import json

def test_task_creation():
    """Test task creation with the new structure"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        print("=== TESTING TASK CREATION ===")
        
        # Test insert with all fields
        test_data = {
            'title': 'Test Task',
            'description': 'Test Description',
            'task_date': '2024-12-25',
            'task_time': '10:00',
            'task_end_time': '11:00',
            'location': 'Test Location',
            'status': 'Not completed',
            'assigned_user_id': 1,
            'owner_id': 1
        }
        
        c.execute('''INSERT INTO tasks 
                     (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (test_data['title'], test_data['description'], test_data['task_date'], 
                  test_data['task_time'], test_data['task_end_time'], test_data['location'], 
                  test_data['status'], test_data['assigned_user_id'], test_data['owner_id']))
        
        conn.commit()
        
        # Verify the insert
        c.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 1")
        last_task = c.fetchone()
        if last_task:
            print(f"✅ Task created successfully with ID: {last_task[0]}")
            print(f"   Title: {last_task[1]}")
            print(f"   Date: {last_task[3]} {last_task[4]}")
            print(f"   Owner ID: {last_task[9]}")
            print(f"   Assigned User ID: {last_task[10]}")
        else:
            print("❌ No task found after insert")
        
        conn.close()
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_task_creation()