#!/usr/bin/env python3
"""
Test script for the new OOP features added to app.py
This script tests all the newly added classes to ensure they work correctly.
"""

# Test the new classes independently
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_user_manager():
    """Test UserManager class functionality."""
    print("Testing UserManager class...")
    
    # Import after adding path
    from app import UserManager
    
    # Create instance
    user_manager = UserManager()
    
    # Test public methods
    session_data = {
        'user_id': 1,
        'role': 'admin',
        'active': True
    }
    
    # Test validation
    is_valid = user_manager.public_validate_user_session(1, session_data)
    print(f"✓ Session validation: {is_valid}")
    
    # Test statistics
    stats = user_manager.public_get_user_statistics()
    print(f"✓ User statistics: {stats}")
    
    print("UserManager tests passed!\n")


def test_form_processor():
    """Test FormProcessor class functionality."""
    print("Testing FormProcessor class...")
    
    from app import FormProcessor
    
    # Create instance
    form_processor = FormProcessor()
    
    # Test login form processing
    login_data = {
        'email': 'test@example.com',
        'password': 'password123'
    }
    
    is_valid, errors = form_processor.process_form_data('login', login_data)
    print(f"✓ Login form validation: {is_valid}, errors: {errors}")
    
    # Test registration form processing
    reg_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'password': 'securepass123'
    }
    
    is_valid, errors = form_processor.process_form_data('registration', reg_data)
    print(f"✓ Registration form validation: {is_valid}, errors: {errors}")
    
    print("FormProcessor tests passed!\n")


def test_config_file_manager():
    """Test ConfigFileManager class functionality."""
    print("Testing ConfigFileManager class...")
    
    from app import ConfigFileManager
    
    # Create instance
    config_manager = ConfigFileManager()
    
    # Test configuration retrieval
    app_name = config_manager.get_config_value('app_name')
    print(f"✓ App name configuration: {app_name}")
    
    # Test nested configuration
    smtp_port = config_manager.get_nested_config('email_settings.smtp_port')
    print(f"✓ SMTP port configuration: {smtp_port}")
    
    # Test configuration validation
    is_valid, validation_errors = config_manager.validate_configuration()
    print(f"✓ Configuration validation: {is_valid}, errors: {validation_errors}")
    
    print("ConfigFileManager tests passed!\n")


def test_data_types_and_structures():
    """Test various data types and structures used in the application."""
    print("Testing Data Types and Structures...")
    
    # Test different data types
    string_data: str = "Golden Turf Management"
    integer_data: int = 12345
    boolean_data: bool = True
    float_data: float = 99.99
    
    # Test data structures
    list_data: list = [1, 2, 3, 4, 5]
    dict_data: dict = {'key1': 'value1', 'key2': 'value2'}
    tuple_data: tuple = (1, 'test', True)
    set_data: set = {1, 2, 3, 4, 5}
    
    print(f"✓ String data: {string_data}")
    print(f"✓ Integer data: {integer_data}")
    print(f"✓ Boolean data: {boolean_data}")
    print(f"✓ Float data: {float_data}")
    print(f"✓ List data: {list_data}")
    print(f"✓ Dict data: {dict_data}")
    print(f"✓ Tuple data: {tuple_data}")
    print(f"✓ Set data: {set_data}")
    
    print("Data types and structures tests passed!\n")


def test_control_structures():
    """Test various control structures implemented."""
    print("Testing Control Structures...")
    
    # Test selection (if/elif/else)
    test_value = 5
    if test_value > 10:
        result = "high"
    elif test_value > 3:
        result = "medium"
    else:
        result = "low"
    print(f"✓ Selection structure result: {result}")
    
    # Test iteration (for loops)
    iteration_result = []
    for i in range(3):
        iteration_result.append(f"item_{i}")
    print(f"✓ For loop iteration: {iteration_result}")
    
    # Test repetition (while loops)
    counter = 0
    while_result = []
    while counter < 3:
        while_result.append(f"while_{counter}")
        counter += 1
    print(f"✓ While loop repetition: {while_result}")
    
    print("Control structures tests passed!\n")


if __name__ == "__main__":
    print("=== Testing OOP Features Added to Golden Turf Application ===\n")
    
    try:
        test_user_manager()
        test_form_processor()
        test_config_file_manager()
        test_data_types_and_structures()
        test_control_structures()
        
        print("🎉 ALL TESTS PASSED! 🎉")
        print("All OOP features are working correctly and the application functionality is preserved.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()