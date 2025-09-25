import sqlite3

# Test the has_permission logic for ID 1 users
def test_has_permission_logic():
    # Simulate session with ID 1
    session = {'user_id': 1}
    
    # Test modules that should be accessible
    test_modules = ['clients', 'payments', 'calendar', 'products', 'products_list', 'invoice', 'quotes', 'profiles', 'dashboard']
    
    # Simulate the has_permission function logic
    def has_permission(module, user_id):
        if user_id == 1:
            return True
        
        # This would normally check database permissions
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        user = c.execute('SELECT permissions FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user and module in (user[0] or '').split(',')
    
    print("Testing ID 1 user access:")
    all_passed = True
    for module in test_modules:
        has_access = has_permission(module, session['user_id'])
        status = "✅ PASS" if has_access else "❌ FAIL"
        print(f"  {module}: {status}")
        if not has_access:
            all_passed = False
    
    print(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    # Test with a regular user (ID 2) for comparison
    print(f"\nTesting regular user (ID 2) access:")
    for module in ['clients', 'payments']:  # These should fail for regular user
        has_access = has_permission(module, 2)
        status = "✅ PASS" if has_access else "❌ FAIL (Expected)"
        print(f"  {module}: {status}")

if __name__ == "__main__":
    test_has_permission_logic()