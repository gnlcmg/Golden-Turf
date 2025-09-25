#!/usr/bin/env python3

import sqlite3
import sys
sys.path.append('.')

# Mock session for testing 
class MockSession:
    def __init__(self):
        self.data = {'user_id': 1}
    
    def get(self, key):
        return self.data.get(key)

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

def get_all_tasks(user_id=None):
    # Mock session
    session = MockSession()
    
    # Get tasks owned by the current session user
    session_user_id = session.get('user_id')
    if not session_user_id:
        return []
    
    if user_id:
        # Filter by assigned user but still respect ownership
        query = 'SELECT * FROM tasks WHERE owner_id = ? AND assigned_user_id = ? ORDER BY task_date, task_time'
        params = (session_user_id, user_id)
        print(f"DEBUG: Filtering by assigned user {user_id}, owner {session_user_id}")
    else:
        # Get all tasks owned by the current session user
        query = 'SELECT * FROM tasks WHERE owner_id = ? ORDER BY task_date, task_time'
        params = (session_user_id,)
        print(f"DEBUG: Getting all tasks for owner {session_user_id}")
    
    print(f"DEBUG: Query: {query}")
    print(f"DEBUG: Params: {params}")
    
    return db_exec(query, params, 'all') or []

def test_task_retrieval():
    """Test task retrieval with different parameters"""
    try:
        print("=== TESTING TASK RETRIEVAL ===")
        
        print("\n1. Get all tasks (no filter):")
        all_tasks = get_all_tasks()
        print(f"Found {len(all_tasks)} tasks")
        for task in all_tasks:
            print(f"  ID: {task[0]}, Title: {task[1]}, Date: {task[3]}, Owner: {task[9] if len(task) > 9 else 'N/A'}")
        
        print("\n2. Get tasks assigned to user 1:")
        user1_tasks = get_all_tasks(1)
        print(f"Found {len(user1_tasks)} tasks assigned to user 1")
        for task in user1_tasks:
            print(f"  ID: {task[0]}, Title: {task[1]}, Date: {task[3]}, Assigned: {task[10] if len(task) > 10 else 'N/A'}")
        
        print("\n3. Get tasks assigned to user 2:")
        user2_tasks = get_all_tasks(2)
        print(f"Found {len(user2_tasks)} tasks assigned to user 2")
        for task in user2_tasks:
            print(f"  ID: {task[0]}, Title: {task[1]}, Date: {task[3]}, Assigned: {task[10] if len(task) > 10 else 'N/A'}")
        
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_task_retrieval()