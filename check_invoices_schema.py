import sqlite3

def check_invoices_schema():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("PRAGMA table_info(invoices)")
    schema = c.fetchall()

    conn.close()
    return schema

if __name__ == "__main__":
    schema = check_invoices_schema()
    for column in schema:
        print(column)
