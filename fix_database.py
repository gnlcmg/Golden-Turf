import sqlite3

def migrate_tasks_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in c.fetchall()]
    if 'status' not in columns:
        c.execute("ALTER TABLE tasks RENAME TO tasks_old")
        c.execute('''CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            task_date TEXT NOT NULL,
            task_time TEXT,
            location TEXT,
            status TEXT NOT NULL DEFAULT 'Not completed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''INSERT INTO tasks (id, title, description, task_date, task_time, location)
                     SELECT id, title, description, task_date, task_time, location FROM tasks_old''')
        c.execute("DROP TABLE tasks_old")
        conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_tasks_table()
