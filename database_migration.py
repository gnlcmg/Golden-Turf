"""
Database Migration Script
Handles database schema updates and optimizations.
"""
import sqlite3
import os
from datetime import datetime

def get_database_path():
    """Get the database path from environment or use default."""
    return os.environ.get('DATABASE_URI', 'sqlite:///users.db').replace('sqlite:///', '')

def run_migration():
    """Run database migrations."""
    db_path = get_database_path()
    print(f"Running database migrations on: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Enable foreign key support
        c.execute("PRAGMA foreign_keys = ON")

        # Migration 1: Add missing columns to users table
        print("Migration 1: Updating users table...")
        c.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in c.fetchall()]

        if 'reset_token' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
            print("  - Added reset_token column")

        if 'token_expiry' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN token_expiry TEXT")
            print("  - Added token_expiry column")

        if 'role' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            # Set first user as admin if exists
            c.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            first_user = c.fetchone()
            if first_user:
                c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (first_user[0],))
            print("  - Added role column")

        if 'permissions' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ''")
            print("  - Added permissions column")

        if 'verification_code' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")
            print("  - Added verification_code column")

        # Migration 2: Update clients table
        print("Migration 2: Updating clients table...")
        c.execute("PRAGMA table_info(clients)")
        columns = [info[1] for info in c.fetchall()]

        if 'owner_id' not in columns:
            c.execute("ALTER TABLE clients ADD COLUMN owner_id INTEGER")
            # Set owner_id to 1 for existing clients (assuming first user is admin)
            c.execute("UPDATE clients SET owner_id = 1 WHERE owner_id IS NULL")
            print("  - Added owner_id column")

        # Migration 3: Update invoices table
        print("Migration 3: Updating invoices table...")
        c.execute("PRAGMA table_info(invoices)")
        columns = [info[1] for info in c.fetchall()]

        if 'owner_id' not in columns:
            c.execute("ALTER TABLE invoices ADD COLUMN owner_id INTEGER")
            c.execute("UPDATE invoices SET owner_id = 1 WHERE owner_id IS NULL")
            print("  - Added owner_id column")

        if 'extras_json' not in columns:
            c.execute("ALTER TABLE invoices ADD COLUMN extras_json TEXT")
            print("  - Added extras_json column")

        # Migration 4: Update tasks table
        print("Migration 4: Updating tasks table...")
        c.execute("PRAGMA table_info(tasks)")
        columns = [info[1] for info in c.fetchall()]

        if 'task_end_time' not in columns:
            c.execute("ALTER TABLE tasks ADD COLUMN task_end_time TEXT")
            print("  - Added task_end_time column")

        if 'assigned_user_id' not in columns:
            c.execute("ALTER TABLE tasks ADD COLUMN assigned_user_id INTEGER")
            print("  - Added assigned_user_id column")

        if 'owner_id' not in columns:
            c.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER")
            c.execute("UPDATE tasks SET owner_id = 1 WHERE owner_id IS NULL")
            print("  - Added owner_id column")

        # Migration 5: Update quotes table
        print("Migration 5: Updating quotes table...")
        c.execute("PRAGMA table_info(quotes)")
        columns = [info[1] for info in c.fetchall()]

        if 'owner_id' not in columns:
            c.execute("ALTER TABLE quotes ADD COLUMN owner_id INTEGER")
            c.execute("UPDATE quotes SET owner_id = 1 WHERE owner_id IS NULL")
            print("  - Added owner_id column")

        # Migration 6: Update jobs table
        print("Migration 6: Updating jobs table...")
        c.execute("PRAGMA table_info(jobs)")
        columns = [info[1] for info in c.fetchall()]

        if 'owner_id' not in columns:
            c.execute("ALTER TABLE jobs ADD COLUMN owner_id INTEGER")
            c.execute("UPDATE jobs SET owner_id = 1 WHERE owner_id IS NULL")
            print("  - Added owner_id column")

        # Migration 7: Create indexes for better performance
        print("Migration 7: Creating performance indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_clients_owner_id ON clients(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_invoices_owner_id ON invoices(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_owner_id ON tasks(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(task_date)",
            "CREATE INDEX IF NOT EXISTS idx_quotes_owner_id ON quotes(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_owner_id ON jobs(owner_id)",
        ]

        for index_sql in indexes:
            try:
                c.execute(index_sql)
                print(f"  - Created index: {index_sql.split()[-1]}")
            except sqlite3.Error as e:
                print(f"  - Failed to create index: {e}")

        # Migration 8: Add created_date to clients if missing
        c.execute("PRAGMA table_info(clients)")
        columns = [info[1] for info in c.fetchall()]
        if 'created_date' not in columns:
            c.execute("ALTER TABLE clients ADD COLUMN created_date TEXT")
            print("  - Added created_date column to clients")

        # Commit all changes
        conn.commit()
        print("\n✅ Database migration completed successfully!")

        # Show migration summary
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        print("
Migration Summary:")
        print(f"  - Total users: {total_users}")
        print(f"  - Admin users: {admin_count}")
        print(f"  - Regular users: {total_users - admin_count}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error during database migration: {str(e)}")
        return False

def create_connection_pool():
    """Create a connection pool for better performance."""
    db_path = get_database_path()

    def get_connection():
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Better performance
        conn.execute("PRAGMA cache_size = 10000")  # 10MB cache
        conn.execute("PRAGMA temp_store = memory")
        conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map
        return conn

    return get_connection

if __name__ == "__main__":
    print("Golden Turf - Database Migration Script")
    print("=" * 50)
    print("This script will update your database schema and add performance optimizations.")
    print("⚠️  WARNING: Make sure to backup your database before running this script!")
    print()

    # Ask for confirmation
    response = input("Do you want to proceed with database migration? (yes/no): ").lower().strip()

    if response in ['yes', 'y']:
        success = run_migration()
        if success:
            print("\n🎉 Migration completed successfully!")
            print("You can now run your application with improved database performance.")
    else:
        print("Migration cancelled.")
