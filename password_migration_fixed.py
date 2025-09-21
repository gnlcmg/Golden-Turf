"""
Password Migration Script
Migrates all plain text passwords to bcrypt hashed passwords.
This script should be run once to fix the security vulnerability.
"""
import sqlite3
import bcrypt
import sys
from datetime import datetime

def migrate_passwords():
    """Migrate all plain text passwords to bcrypt hashed passwords."""
    print("Starting password migration...")

    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Get all users with their passwords
        c.execute('SELECT id, name, email, password FROM users')
        users = c.fetchall()

        migrated_count = 0
        skipped_count = 0

        for user in users:
            user_id, name, email, password = user

            # Check if password is already hashed (bcrypt format)
            if isinstance(password, str) and (password.startswith('$2b$') or password.startswith('$2a$')):
                print(f"Skipping user {name} ({email}) - password already hashed")
                skipped_count += 1
                continue

            # Check if password is plain text
            if isinstance(password, str) and not password.startswith('$'):
                # Hash the plain text password
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                # Update the user record
                c.execute('UPDATE users SET password = ? WHERE id = ?',
                         (hashed_password.decode('utf-8'), user_id))

                print(f"Migrated password for user: {name} ({email})")
                migrated_count += 1
            else:
                print(f"Skipping user {name} ({email}) - password format unknown")
                skipped_count += 1

        # Commit all changes
        conn.commit()
        conn.close()

        print("
Password migration completed!")
        print(f"Total users processed: {len(users)}")
        print(f"Passwords migrated: {migrated_count}")
        print(f"Passwords skipped: {skipped_count}")

        if migrated_count > 0:
            print("
⚠️  WARNING: This migration has been applied.")
            print("All plain text passwords have been converted to bcrypt hashes.")
            print("You can now delete this script for security reasons.")

        return True

    except Exception as e:
        print(f"Error during password migration: {str(e)}")
        return False

def verify_migration():
    """Verify that all passwords are now properly hashed."""
    print("\nVerifying password migration...")

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute('SELECT id, name, email, password FROM users')
        users = c.fetchall()

        properly_hashed = 0
        improperly_hashed = 0

        for user in users:
            user_id, name, email, password = user

            if isinstance(password, str) and (password.startswith('$2b$') or password.startswith('$2a$')):
                properly_hashed += 1
            else:
                improperly_hashed += 1
                print(f"User {name} ({email}) has improperly hashed password")

        conn.close()

        print("
Verification Results:")
        print(f"Properly hashed passwords: {properly_hashed}")
        print(f"Improperly hashed passwords: {improperly_hashed}")

        if improperly_hashed == 0:
            print("✅ All passwords are properly hashed!")
            return True
        else:
            print("❌ Some passwords are still not properly hashed!")
            return False

    except Exception as e:
        print(f"Error during verification: {str(e)}")
        return False

if __name__ == "__main__":
    print("Golden Turf - Password Migration Script")
    print("=" * 50)
    print("This script will migrate all plain text passwords to bcrypt hashes.")
    print("⚠️  WARNING: Make sure to backup your database before running this script!")
    print()

    # Ask for confirmation
    response = input("Do you want to proceed with password migration? (yes/no): ").lower().strip()

    if response in ['yes', 'y']:
        success = migrate_passwords()
        if success:
            verify_migration()
    else:
        print("Migration cancelled.")
        sys.exit(0)
