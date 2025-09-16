import sqlite3

def check_invoices_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(invoices)")
    columns = c.fetchall()
    conn.close()

    print("Invoices Table Structure:")
    for column in columns:
        print(column)

if __name__ == "__main__":
    check_invoices_table()