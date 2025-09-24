import sqlite3
import bcrypt

def fix_users_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        print("Starting users table migration...")
        
        # First, check if password_hash column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'password_hash' not in column_names:
            print("Adding password_hash column...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash BLOB")
        
        # Get all users with non-null passwords but null password_hash
        cursor.execute("SELECT id, password FROM users WHERE password IS NOT NULL AND (password_hash IS NULL OR password_hash = '')")
        users_to_migrate = cursor.fetchall()
        
        print(f"Found {len(users_to_migrate)} users to migrate...")
        
        # Migrate existing passwords to password_hash
        for user_id, old_password in users_to_migrate:
            if old_password and old_password.strip():
                new_hash = bcrypt.hashpw(old_password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
                print(f"Migrated password for user ID {user_id}")
        
        # Now create a new table with the correct structure
        print("Creating new users table structure...")
        
        cursor.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash BLOB,
                reset_token TEXT,
                token_expiry TEXT,
                role TEXT DEFAULT 'user',
                verification_code TEXT,
                permissions TEXT DEFAULT 'dashboard'
            )
        ''')
        
        # Copy data from old table to new table
        cursor.execute('''
            INSERT INTO users_new (id, name, email, password_hash, reset_token, token_expiry, role, verification_code, permissions)
            SELECT id, name, email, password_hash, reset_token, token_expiry, role, verification_code, permissions
            FROM users
        ''')
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # Reset the sqlite_sequence for the users table
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'users'")
        cursor.execute("SELECT MAX(id) FROM users")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (max_id,))
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the new structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("\nNew users table schema:")
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else "NULL"
            default_val = f"DEFAULT: {col[4]}" if col[4] else ""
            print(f"  {col_name} {col_type} {not_null} {default_val}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_users_table()