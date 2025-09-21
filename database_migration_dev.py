"""
Database migration script for Golden Turf development environment.
Updates database schema and adds security/performance improvements.
"""
import sqlite3
import sys
from datetime import datetime

def get_database_path():
    """Get the correct database path for development."""
    return 'dev_users.db'

def run_migration():
    """Run database migrations."""
    db_path = get_database_path()

    print("Golden Turf - Database Migration Script")
    print("=" * 50)
    print(f"This script will update your database schema and add performance optimizations.")
    print(f"⚠️  WARNING: Make sure to backup your database before running this script!")
    print()

    # Get user confirmation
    response = input("Do you want to proceed with database migration? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        return

    print(f"Running database migrations on: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Migration 1: Update users table
        print("Migration 1: Updating users table...")
        try:
            # Check existing columns
            c.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in c.fetchall()]

            # Add missing columns
            if 'role' not in columns:
                c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
                print("  - Added 'role' column to users table")

            if 'permissions' not in columns:
                c.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ''")
                print("  - Added 'permissions' column to users table")

            if 'reset_token' not in columns:
                c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
                print("  - Added 'reset_token' column to users table")

            if 'token_expiry' not in columns:
                c.execute("ALTER TABLE users ADD COLUMN token_expiry TEXT")
                print("  - Added 'token_expiry' column to users table")

            if 'verification_code' not in columns:
                c.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")
                print("  - Added 'verification_code' column to users table")

        except sqlite3.Error as e:
            print(f"  - Error updating users table: {e}")

        # Migration 2: Update clients table
        print("Migration 2: Updating clients table...")
        try:
            c.execute("PRAGMA table_info(clients)")
            columns = [info[1] for info in c.fetchall()]

            if 'owner_id' not in columns:
                c.execute("ALTER TABLE clients ADD COLUMN owner_id INTEGER")
                print("  - Added 'owner_id' column to clients table")

        except sqlite3.Error as e:
            print(f"  - Error updating clients table: {e}")

        # Migration 3: Update invoices table
        print("Migration 3: Updating invoices table...")
        try:
            c.execute("PRAGMA table_info(invoices)")
            columns = [info[1] for info in c.fetchall()]

            if 'owner_id' not in columns:
                c.execute("ALTER TABLE invoices ADD COLUMN owner_id INTEGER")
                print("  - Added 'owner_id' column to invoices table")

            if 'extras_json' not in columns:
                c.execute("ALTER TABLE invoices ADD COLUMN extras_json TEXT")
                print("  - Added 'extras_json' column to invoices table")

        except sqlite3.Error as e:
            print(f"  - Error updating invoices table: {e}")

        # Migration 4: Update tasks table
        print("Migration 4: Updating tasks table...")
        try:
            c.execute("PRAGMA table_info(tasks)")
            columns = [info[1] for info in c.fetchall()]

            if 'task_end_time' not in columns:
                c.execute("ALTER TABLE tasks ADD COLUMN task_end_time TEXT")
                print("  - Added 'task_end_time' column to tasks table")

            if 'assigned_user_id' not in columns:
                c.execute("ALTER TABLE tasks ADD COLUMN assigned_user_id INTEGER")
                print("  - Added 'assigned_user_id' column to tasks table")

            if 'owner_id' not in columns:
                c.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER")
                print("  - Added 'owner_id' column to tasks table")

        except sqlite3.Error as e:
            print(f"  - Error updating tasks table: {e}")

        # Migration 5: Update quotes table
        print("Migration 5: Updating quotes table...")
        try:
            c.execute("PRAGMA table_info(quotes)")
            columns = [info[1] for info in c.fetchall()]

            if 'owner_id' not in columns:
                c.execute("ALTER TABLE quotes ADD COLUMN owner_id INTEGER")
                print("  - Added 'owner_id' column to quotes table")

        except sqlite3.Error as e:
            print(f"  - Error updating quotes table: {e}")

        # Migration 6: Update jobs table
        print("Migration 6: Updating jobs table...")
        try:
            c.execute("PRAGMA table_info(jobs)")
            columns = [info[1] for info in c.fetchall()]

            if 'owner_id' not in columns:
                c.execute("ALTER TABLE jobs ADD COLUMN owner_id INTEGER")
                print("  - Added 'owner_id' column to jobs table")

        except sqlite3.Error as e:
            print(f"  - Error updating jobs table: {e}")

        # Migration 7: Create performance indexes
        print("Migration 7: Creating performance indexes...")
        indexes = [
            ("users", "email"),
            ("users", "role"),
            ("clients", "owner_id"),
            ("invoices", "owner_id"),
            ("invoices", "client_id"),
            ("tasks", "owner_id"),
            ("tasks", "task_date"),
            ("quotes", "owner_id"),
            ("jobs", "owner_id"),
        ]

        for table, column in indexes:
            try:
                index_name = f"idx_{table}_{column}"
                c.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})")
                print(f"  - Created index: {index_name}")
            except sqlite3.Error as e:
                print(f"  - Error creating index {index_name}: {e}")

        # Set first user as admin
        print("Setting up admin user...")
        c.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = c.fetchone()
        if first_user:
            c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (first_user[0],))
            print(f"  - Set user ID {first_user[0]} as admin")

        # Get user counts
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_users = c.fetchone()[0]

        regular_users = total_users - admin_users

        conn.commit()
        conn.close()

        print()
        print("✅ Database migration completed successfully!")
        print()
        print("Migration Summary:")
        print(f"  - Total users: {total_users}")
        print(f"  - Admin users: {admin_users}")
        print(f"  - Regular users: {regular_users}")
        print()
        print("🎉 Migration completed successfully!")
        print("You can now run your application with improved database performance.")

    except sqlite3.Error as e:
        print(f"❌ Database migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
