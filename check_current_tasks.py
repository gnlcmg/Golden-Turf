#!/usr/bin/env python3

import sqlite3

def check_current_tasks():
    """Check what tasks exist in the database"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        print("=== CURRENT TASKS IN DATABASE ===")
        c.execute("SELECT * FROM tasks ORDER BY id")
        tasks = c.fetchall()
        
        if not tasks:
            print("No tasks found in database")
        else:
            print(f"Found {len(tasks)} tasks:")
            for task in tasks:
                print(f"ID: {task[0]}, Title: {task[1]}, Date: {task[3]}, Time: {task[4]}, Owner: {task[9]}, Assigned: {task[10]}")
        
        print("\n=== USERS IN DATABASE ===")
        c.execute("SELECT id, name, email FROM users ORDER BY id")
        users = c.fetchall()
        for user in users:
            print(f"User ID: {user[0]}, Name: {user[1]}, Email: {user[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    check_current_tasks()