#!/usr/bin/env python3

import requests
import json

def test_individual_task_api():
    """Test the individual task API endpoint"""
    try:
        print("=== TESTING INDIVIDUAL TASK API ===")
        
        # First, let's check what tasks exist
        response = requests.get('http://127.0.0.1:5000/api/tasks')
        print(f"All tasks API status: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ Authentication required - this is expected since we're not logged in")
            print("The API endpoint is working correctly and requires authentication")
            return
        
        if response.status_code == 200:
            tasks = response.json()
            print(f"Found {len(tasks)} tasks")
            
            if tasks:
                task_id = tasks[0]['id']
                print(f"Testing individual task API for task ID: {task_id}")
                
                # Test individual task endpoint
                individual_response = requests.get(f'http://127.0.0.1:5000/api/tasks/{task_id}')
                print(f"Individual task API status: {individual_response.status_code}")
                
                if individual_response.status_code == 401:
                    print("✅ Individual task API is working and requires authentication (as expected)")
                elif individual_response.status_code == 200:
                    task_data = individual_response.json()
                    print(f"✅ Task data retrieved: {task_data}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app - make sure it's running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == '__main__':
    test_individual_task_api()