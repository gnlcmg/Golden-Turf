from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mail import Mail, Message
from flask_cors import CORS
from bcrypt import hashpw, gensalt, checkpw
import sqlite3
import re
import string
import secrets
from datetime import datetime, timedelta
from calendar import Calendar
app = Flask(__name__)
mail = Mail(app)
CORS(app, supports_credentials=True)

app.config['MAIL_SUPPRESS_SEND'] = True
app.secret_key = 'REPLACE_THIS_WITH_A_RANDOM_SECRET_KEY_1234567890'

def has_permission(module):
    """
    Check if the current user has permission for a specific module.
    Returns True if user is admin, user_id is 1, or has specific permission.
    Handles both old permission names and new granular permissions.
    """
    if 'user_role' not in session:
        return False
    if session.get('user_role') == 'admin' or session.get('user_id') == 1:
        return True
    user_permissions = session.get('user_permissions', '')
    if not user_permissions:
        return False
    permissions_list = [p.strip() for p in user_permissions.split(',') if p.strip()]

    # Handle backward compatibility for old permission names
    if module == 'products':
        # Old 'products' permission now maps to multiple product permissions
        product_permissions = ['turf_products', 'artificial_hedges', 'fountains', 'bamboo_products', 'pebbles', 'pegs', 'adhesive_tape']
        return any(perm in permissions_list for perm in product_permissions)

    return module in permissions_list

def can_change_role(current_user_id, target_user_id):
    """
    Check if current user can change the role of target user.
    Users cannot change their own role.
    """
    if current_user_id == target_user_id:
        return False
    return True

def can_demote_admin(target_user_id, new_role):
    """
    Check if it's safe to demote an admin user.
    Cannot demote if this would leave no admins. Any admin, including ID 1, can be demoted as long as at least one admin remains after.
    """
    if new_role != 'admin':
        # Check if this would leave at least one admin after demotion
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        conn.close()

        # If this user is currently admin and we're demoting them,
        # and there would be zero admins left, prevent the demotion
        if admin_count == 1:
            return False

    return True

def migrate_users_table():
    """
    Migrate users table to add missing columns.
    """
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in c.fetchall()]

    if 'reset_token' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        print("Added reset_token column to users table")

    if 'token_expiry' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN token_expiry TEXT")
        print("Added token_expiry column to users table")

    if 'role' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        # Set first user as admin if exists
        c.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = c.fetchone()
        if first_user:
            c.execute("UPDATE users SET role = 'admin' WHERE id = ?", (first_user[0],))
        print("Added role column to users table")

    if 'permissions' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ''")
        print("Added permissions column to users table")

    if 'verification_code' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN verification_code TEXT")
        print("Added verification_code column to users table")

    conn.commit()
    conn.close()



@app.route('/', methods=['GET'])
def home():
    """Root route - redirect to login page"""
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('All fields are required.')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.')
            return render_template('register.html')

        hashed_password = hashpw(password.encode('utf-8'), gensalt())

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        # All manually added users start as 'user' role
        # Only user ID 1 (first user) will be admin by default
        role = 'user'
        permissions = ''  # No permissions by default
        try:
            c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                      (name, email, hashed_password.decode('utf-8'), role, permissions))
            conn.commit()
            flash('Registration successful!')
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered!')
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Removed check to always allow access to login page
    # if 'user_name' in session:
    #     print("User already logged in, redirecting to dashboard.")  # Debugging log
    #     return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        print(f"Login attempt: email={email}, password={password}")  # Debugging log
        if not email or not password:
            flash('Please enter email and password.')
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id, name, role, password, permissions FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            print(f"User fetched from database: {user}")  # Debugging log
            if user:
                stored_password = user[3]
                # Check if stored_password is hashed (starts with $2b$ or $2a$ for bcrypt)
                if isinstance(stored_password, str) and (stored_password.startswith('$2b$') or stored_password.startswith('$2a$')):
                    try:
                        hashed_password = stored_password.encode('utf-8')
                        if checkpw(password.encode('utf-8'), hashed_password):
                            session['user_id'] = user[0]
                            session['user_name'] = user[1]
                            session['user_role'] = user[2] if user[2] else 'user'
                            session['user_permissions'] = user[4] if user[4] else ''
                            print(f"Session set: user_id={session['user_id']}, user_name={session['user_name']}, user_role={session['user_role']}, user_permissions={session['user_permissions']}")  # Debugging log

                            # Always assign the user's own database (named uniquely, e.g., by email)
                            session['database'] = f'{email}_db.sqlite'
                            print("Assigned user's own database.")  # Debugging log

                            # Create a new empty database for the user if it doesn't exist
                            user_db = sqlite3.connect(session['database'])
                            user_db.execute('''CREATE TABLE IF NOT EXISTS clients (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                client_name TEXT NOT NULL,
                                email TEXT,
                                phone TEXT,
                                account_type TEXT,
                                company_name TEXT,
                                actions TEXT,
                                created_date TEXT
                            )''')
                            user_db.commit()
                            user_db.close()

                            conn.close()
                            print("Redirecting to dashboard.")  # Debugging log
                            return redirect(url_for('dashboard'))
                        else:
                            # flash('Invalid email or password.')
                            print("Password mismatch.")  # Debugging log
                    except ValueError:
                        flash('Invalid password format. Please reset your password.')
                        print("Invalid password format.")  # Debugging log
                else:
                    # Password is stored in plain text or unknown format, compare directly (not secure)
                    if password == stored_password:
                        session['user_id'] = user[0]
                        session['user_name'] = user[1]
                        session['user_role'] = user[2] if user[2] else 'user'
                        session['user_permissions'] = user[4] if user[4] else ''
                        print(f"Session set: user_id={session['user_id']}, user_name={session['user_name']}, user_role={session['user_role']}, user_permissions={session['user_permissions']}")  # Debugging log

                        # Always assign the user's own database (named uniquely, e.g., by email)
                        session['database'] = f'{email}_db.sqlite'
                        print("Assigned user's own database.")  # Debugging log

                        # Create a new empty database for the user if it doesn't exist
                        user_db = sqlite3.connect(session['database'])
                        user_db.execute('''CREATE TABLE IF NOT EXISTS clients (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            client_name TEXT NOT NULL,
                            email TEXT,
                            phone TEXT,
                            account_type TEXT,
                            company_name TEXT,
                            actions TEXT,
                            created_date TEXT
                        )''')
                        user_db.commit()
                        user_db.close()

                        conn.close()
                        print("Redirecting to dashboard.")  # Debugging log
                        return redirect(url_for('dashboard'))
                    else:
                        # flash('Invalid email or password.')
                        print("Password mismatch.")  # Debugging log
            else:
                # flash('Invalid email or password.')
                print("User not found in database.")  # Debugging log
            conn.close()
    print("Login failed.")  # Debugging log
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        print("Dashboard access denied: No user_name in session")  # Debugging log
        return redirect(url_for('login'))

    if not has_permission('dashboard'):
        return redirect(url_for('access_restricted'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    print(f"Dashboard accessed: user_name={session.get('user_name')}, user_role={session.get('user_role')}")  # Debugging log

    user_role = session.get('user_role', 'user')
    
    # Get ALL data for dashboard - both admin and users should see the same totals
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Get all clients
    c.execute('SELECT * FROM clients')
    clients = c.fetchall()
    
    # Get all jobs
    c.execute('SELECT * FROM jobs')
    jobs = c.fetchall()
    
    # Get all invoices/payments
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date, 
                        invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.owner_id
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  ORDER BY invoices.created_date DESC''')
    payments = c.fetchall()
    
    conn.close()

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)

    total_clients = len(clients)

    # Fix sales calculations to use proper invoice data  
    # Query result format: [id, client_name, status, created_date, product, quantity, price, gst, total, owner_id]
    # Index 8 is the total amount, index 2 is the status, index 3 is created_date
    
    # Calculate sales only from PAID invoices (status != 'Unpaid')
    paid_payments = [payment for payment in payments if payment[2] != 'Unpaid']
    
    # Also calculate total sales from ALL invoices for comparison
    total_all_invoices = sum(float(payment[8]) for payment in payments if payment[8] is not None)
    
    total_sales_paid_only = sum(float(payment[8]) for payment in paid_payments if payment[8] is not None)
    
    # Calculate time-based sales (only from PAID invoices)
    today_sales = 0
    yesterday_sales = 0
    last_7_days_sales = 0
    
    for payment in paid_payments:  # Only iterate through paid invoices
        if payment[8] is not None and payment[3]:  # Has total and date
            try:
                invoice_date = datetime.strptime(payment[3], '%Y-%m-%d %H:%M:%S').date()
                amount = float(payment[8])
                
                if invoice_date == today:
                    today_sales += amount
                elif invoice_date == yesterday:
                    yesterday_sales += amount
                    
                if invoice_date >= last_7_days:
                    last_7_days_sales += amount
                    
            except (ValueError, TypeError) as e:
                print(f"Date parsing error for payment {payment[0]}: {e}")
                continue
    
    # Debug output
    print(f"DEBUG - Dashboard calculations for user {session.get('user_name')} (role: {user_role}):")
    print(f"  Total invoices found: {len(payments)}")
    print(f"  Paid invoices: {len(paid_payments)}")
    print(f"  Total sales (ALL invoices): ${total_all_invoices}")
    print(f"  Total sales (PAID only): ${total_sales_paid_only}")
    print(f"  Today sales: ${today_sales}")
    print(f"  Yesterday sales: ${yesterday_sales}") 
    print(f"  Last 7 days sales: ${last_7_days_sales}")
    print(f"  Date ranges: today={today}, yesterday={yesterday}, last_7_days={last_7_days}")
    print(f"  Invoice statuses: {[p[2] for p in payments[:5]]}...")  # Show first 5 invoice statuses

    upcoming_jobs = [job for job in jobs if datetime.strptime(job[2], '%Y-%m-%d').date() >= today]
    overdue_jobs = [job for job in jobs if datetime.strptime(job[2], '%Y-%m-%d').date() < today and job[3] != 'Completed']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    overdue_jobs_info = []
    for job in overdue_jobs:
        c.execute('SELECT client_name FROM clients WHERE id = ?', (job[1],))  # Removed owner_id restriction
        client_name = c.fetchone()
        if client_name:
            overdue_jobs_info.append({'client_name': client_name[0], 'job_date': job[2]})
    conn.close()

    # Fetch admin users
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name, email FROM users WHERE role = 'admin'")
    admins = c.fetchall()
    conn.close()

    return render_template('dashboard_updated.html',
                           total_clients=total_clients,
                           total_sales=total_sales_paid_only,  # Show only paid invoices
                           total_all_sales=total_all_invoices,  # Include all invoices total for debugging
                           today_sales=today_sales,
                           yesterday_sales=yesterday_sales,
                           last_7_days_sales=last_7_days_sales,
                           overdue_jobs=overdue_jobs_info,
                           user_role=user_role,
                           admins=admins)

def get_all_tasks(user_id=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if user_id:
        c.execute('SELECT * FROM tasks WHERE owner_id = ? ORDER BY task_date, task_time', (user_id,))
    else:
        c.execute('SELECT * FROM tasks ORDER BY task_date, task_time')
    tasks = c.fetchall()
    conn.close()
    return tasks

def query_all_clients(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM clients')  # Removed owner_id restriction - all users see all clients
    clients = c.fetchall()
    conn.close()
    return clients

def query_all_jobs(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM jobs WHERE owner_id = ?', (user_id,))
    jobs = c.fetchall()
    conn.close()
    return jobs

def query_all_payments(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Updated query to ensure we get owner_id and all invoice data properly
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date, 
                        invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.owner_id
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  WHERE invoices.owner_id = ?
                  ORDER BY invoices.created_date DESC''', (user_id,))
    payments = c.fetchall()
    conn.close()
    return payments

def migrate_clients_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(clients)")
    columns = [info[1] for info in c.fetchall()]
    if 'email' not in columns or 'created_date' not in columns:
        c.execute("ALTER TABLE clients RENAME TO clients_old")
        c.execute('''CREATE TABLE clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            account_type TEXT,
            company_name TEXT,
            actions TEXT,
            created_date TEXT,
            UNIQUE(client_name)
        )''')
        c.execute('''INSERT INTO clients (id, client_name) SELECT id, client_name FROM clients_old''')
        c.execute("DROP TABLE clients_old")
        conn.commit()
    conn.close()

def create_tasks_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        task_date TEXT NOT NULL,
        task_time TEXT,
        task_end_time TEXT,
        location TEXT,
        status TEXT NOT NULL DEFAULT 'Not completed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def migrate_tasks_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in c.fetchall()]
    if 'task_end_time' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN task_end_time TEXT")
        conn.commit()
    if 'assigned_user_id' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN assigned_user_id INTEGER")
        conn.commit()
    conn.close()

def migrate_clients_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(clients)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE clients ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing clients (assuming first user is admin)
        c.execute("UPDATE clients SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_invoices_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(invoices)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE invoices ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing invoices
        c.execute("UPDATE invoices SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_tasks_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing tasks
        c.execute("UPDATE tasks SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_quotes_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(quotes)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE quotes ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing quotes
        c.execute("UPDATE quotes SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_jobs_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE jobs ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing jobs
        c.execute("UPDATE jobs SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

migrate_clients_table()
create_tasks_table()
migrate_tasks_table()
migrate_users_table()
migrate_clients_owner_id()
migrate_invoices_owner_id()
migrate_tasks_owner_id()
migrate_quotes_owner_id()
migrate_jobs_owner_id()

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    error = None
    success = None

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        account_type = request.form.get('account_type', '').strip()
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        actions = request.form.get('actions', '').strip()
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        import re
        if not re.match(r'^[A-Za-z ]+$', contact_name):
            error = 'Contact name is required and must contain only alphabetic characters and spaces.'
        elif phone_number and (not phone_number.isdigit()):
            error = 'Phone number must contain digits only if provided.'
        elif account_type not in ['Active', 'Deactivated']:
            error = 'Invalid account type selected.'
        elif '@' not in email or '.' not in email:
            error = 'Invalid email format.'

        if not error:
            c.execute('''INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (contact_name, email, phone_number, account_type, company_name, actions, created_date, user_id))
            conn.commit()
            success = 'Client saved successfully.'

    c.execute('SELECT * FROM clients')  # Removed owner_id restriction - all users see all clients
    clients = c.fetchall()
    print(f"DEBUG: User {user_id} can see {len(clients)} clients (all shared)")
    conn.close()

    return render_template('clients.html', clients=clients, error=error, success=success)

@app.route('/logout')
def logout():
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/access_restricted')
def access_restricted():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    # User with ID 1 always has access
    if session.get('user_id') == 1:
        return redirect(url_for('dashboard'))
    return render_template('access_restricted.html')

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('profiles'):
        return redirect(url_for('access_restricted'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if not name or not email or not password:
            flash('All fields are required.')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long.')
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            permissions = ''  # No permissions by default for new users
            try:
                c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, password, 'user', permissions))
                conn.commit()
                flash('User added successfully!')
            except sqlite3.IntegrityError:
                flash('Email already exists!')
            conn.close()

        return redirect(url_for('profiles'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Do not forcibly set user ID 1 as admin; allow demotion if at least one admin remains
    c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
    users = c.fetchall()
    # Find all admin users
    c.execute('SELECT id FROM users WHERE role = "admin"')
    admin_ids = [row[0] for row in c.fetchall()]
    conn.close()
    # If only one admin, pass that admin's id for disabling
    only_admin_id = admin_ids[0] if len(admin_ids) == 1 else None
    return render_template('profiles.html', users=users, only_admin_id=only_admin_id)

@app.route('/profiles/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Check if the user being deleted is the current user
    is_self_delete = user_id == session.get('user_id')
    # Delete the user
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()

    # Reorder IDs sequentially
    c.execute('SELECT id FROM users ORDER BY id')
    users = c.fetchall()
    for index, user in enumerate(users, start=1):
        c.execute('UPDATE users SET id = ? WHERE id = ?', (index, user[0]))
    conn.commit()

    # Reset the sqlite_sequence to ensure next insert uses sequential ID
    c.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name='users'")
    conn.commit()

    # After deletion, check if any admins remain
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = c.fetchone()[0]
    if admin_count == 0:
        # Promote user ID 1 to admin if exists
        c.execute('SELECT id FROM users WHERE id = 1')
        user1 = c.fetchone()
        if user1:
            c.execute('UPDATE users SET role = "admin" WHERE id = 1')
            conn.commit()

    conn.close()

    if is_self_delete:
        session.clear()
        flash('Your account was deleted. If no admins remained, user ID 1 is now admin.')
        return redirect(url_for('login'))

    flash('User deleted successfully!')
    return redirect(url_for('profiles'))

@app.route('/profiles/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Check if there is only one admin in the system (after connection)
    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    only_one_admin = c.fetchone()[0] == 1
    session['only_one_admin'] = only_one_admin

    c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        # Role and permissions may be disabled for self-edit, so get from DB if not in form
        role = request.form.get('role') or (user[3] if user else 'user')
        permissions = ','.join(request.form.getlist('permissions')) if request.form.getlist('permissions') else (user[4] if user else '')

        current_user_id = session.get('user_id')

        # Prevent demoting user ID 1 or the only admin
        is_id1 = user_id == 1
        only_one_admin = (user and user[3] == 'admin' and session.get('only_one_admin'))
        if (is_id1 or only_one_admin) and role != 'admin':
            flash('User ID 1 and the only admin must always remain admin.')
        elif not name or not email:
            flash('Name and email are required.')
        elif len(password) < 6 and password:
            flash('Password must be at least 6 characters long if provided.')
        else:
            if password:
                c.execute('UPDATE users SET name = ?, email = ?, password = ?, role = ?, permissions = ? WHERE id = ?',
                          (name, email, password, role, permissions, user_id))
            else:
                c.execute('UPDATE users SET name = ?, email = ?, role = ?, permissions = ? WHERE id = ?',
                          (name, email, role, permissions, user_id))
            conn.commit()
            flash('User updated successfully!')
            conn.close()
            return redirect(url_for('profiles'))

    conn.close()

    if not user:
        flash('User not found.')
        return redirect(url_for('profiles'))

    # For admins, always show all permissions as checked and disabled
    is_admin = user and user[3] == 'admin'
    all_permissions = ['dashboard', 'clients', 'products_list', 'quotes', 'payments', 'calendar', 'profiles']
    user_permissions = user[4].split(',') if user and user[4] else []
    return render_template('edit_user.html', user=user, is_admin=is_admin, all_permissions=all_permissions, user_permissions=user_permissions)

@app.route('/profiles/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    current_user_id = session.get('user_id')

    if not can_change_role(current_user_id, user_id):
        flash('You cannot change your own role.')
        return redirect(url_for('profiles'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    current_role = c.fetchone()[0]
    new_role = 'user' if current_role == 'admin' else 'admin'

    if not can_demote_admin(user_id, new_role):
        # Check admin count for error message
        conn2 = sqlite3.connect('users.db')
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c2.fetchone()[0]
        conn2.close()
        if admin_count == 1:
            flash('Cannot remove admin rights if only one admin remains.')
        else:
            flash('Cannot remove admin rights.')
        conn.close()
        return redirect(url_for('profiles'))

    c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()

    # If the current user is revoking their own admin, update session and redirect
    if user_id == current_user_id and new_role == 'user':
        session['user_role'] = 'user'
        flash('You have revoked your own admin rights. Access is now restricted.')
        return redirect(url_for('access_restricted'))

    flash(f'User role updated to {new_role}!')
    return redirect(url_for('profiles'))

@app.route('/profiles/update_permissions/<int:user_id>', methods=['POST'])
def update_permissions(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    # Get list of permissions from checkboxes
    permissions_list = request.form.getlist('permissions')
    permissions = ','.join(permissions_list)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET permissions = ? WHERE id = ?', (permissions, user_id))
    conn.commit()
    conn.close()

    # If the current user's permissions were updated, update session immediately
    if user_id == session.get('user_id'):
        session['user_permissions'] = permissions

    flash('User permissions updated!')
    return redirect(url_for('profiles'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            message = 'Please enter your email address.'
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            if user:
                # Generate 6-digit verification code
                verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                token_expiry = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
                c.execute('UPDATE users SET verification_code = ?, token_expiry = ? WHERE email = ?', (verification_code, token_expiry, email))
                conn.commit()

                # Send email with verification code
                msg = Message('Your Verification Code', sender='noreply@goldenturf.com', recipients=[email])
                msg.body = f'Your verification code is: {verification_code}'
                mail.send(msg)  # Uncommented to enable email sending

                conn.close()
                return redirect(url_for('verify_code', email=email))
            else:
                message = 'If this email is registered, a verification code has been sent.'
            conn.close()
    return render_template('forgotpassword.html', message=message)

@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    message = ''
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not new_password or not confirm_password:
            message = 'Please fill in all fields.'
        elif len(new_password) < 6:
            message = 'Password must be at least 6 characters long.'
        elif new_password != confirm_password:
            message = 'Passwords do not match.'
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ? AND token_expiry > ?', (email, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            user = c.fetchone()
            if user:
                c.execute('UPDATE users SET password = ?, verification_code = NULL, token_expiry = NULL WHERE id = ?', (new_password, user[0]))
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            else:
                message = 'Invalid or expired reset token.'
                conn.close()

    return render_template('reset_password.html', message=message, email=email)

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('invoice'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    # Fetch all product prices from DB for dynamic pricing
    c.execute('SELECT product_name, price FROM products')
    price_table = {}
    for row in c.fetchall():
        try:
            price_table[row[0]] = float(row[1]) if row[1] else 0.0
        except (ValueError, TypeError):
            # Handle non-numeric prices like "Custom"
            price_table[row[0]] = 0.0


    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        turf_type = request.form.get('turf_type', '').strip()
        area_val = request.form.get('area', type=float)
        payment_status = request.form.get('payment_status', '').strip()
        gst = request.form.get('gst') == 'yes'

        # Calculate base price
        base_price = price_table.get(turf_type, 0) * area_val if area_val else 0

        # Calculate extras cost
        extras_cost = 0
        extras_details = []

        # Artificial Hedges
        hedges_qty = request.form.get('artificial_hedges_qty', type=int)
        if hedges_qty and hedges_qty > 0:
            extras_cost += 60 * hedges_qty
            extras_details.append(f"Artificial Hedges: {hedges_qty}")

        # Fountain
        fountain_price = request.form.get('fountain_price', type=float)
        db_fountain_price = price_table.get('Fountains', 0)
        if fountain_price and fountain_price > 0:
            extras_cost += fountain_price
            extras_details.append(f"Fountain: ${fountain_price}")
        elif db_fountain_price:
            extras_cost += db_fountain_price
            extras_details.append(f"Fountain: ${db_fountain_price}")

        # Bamboo Products
        bamboo_size = request.form.get('bamboo_products_size')
        bamboo_qty = request.form.get('bamboo_products_qty', type=int)
        if bamboo_size and bamboo_qty and bamboo_qty > 0:
            bamboo_key = f"Bamboo ({bamboo_size})" if bamboo_size in ['2m', '2.4m', '1.8m'] else None
            bamboo_price = price_table.get(bamboo_key, 0)
            extras_cost += bamboo_price * bamboo_qty
            extras_details.append(f"Bamboo {bamboo_size}: {bamboo_qty}")

        # Pebbles (merged, custom type)
        pebbles_custom_type = request.form.get('pebbles_custom_type')
        pebbles_qty = request.form.get('pebbles_qty', type=int)
        if pebbles_custom_type and pebbles_qty and pebbles_qty > 0:
            if pebbles_custom_type.lower() in ['multicolour', 'glow']:
                pebbles_price = price_table.get('Pebbles Multicolour/Glow', 0)
            else:
                pebbles_price = price_table.get('Pebbles Standard', 0)
            extras_cost += pebbles_price * pebbles_qty
            extras_details.append(f"Pebbles ({pebbles_custom_type}): {pebbles_qty}")

        # Pegs
        pegs_qty = request.form.get('pegs_qty', type=int)
        if pegs_qty and pegs_qty > 0:
            extras_cost += 25 * pegs_qty
            extras_details.append(f"Pegs: {pegs_qty}")

        # Adhesive Tape
        tape_qty = request.form.get('adhesive_tape_qty', type=int)
        if tape_qty and tape_qty > 0:
            extras_cost += 25 * tape_qty
            extras_details.append(f"Adhesive Tape: {tape_qty}")

        # Total price calculation
        price = base_price + extras_cost
        gst_amount = price * 0.10 if gst else 0
        total_price = price + gst_amount

        # Get client_id from client_name and validate
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client_row = c.fetchone()
        if not client_row:
            # Client not found, show error and do not save invoice
            c.execute('SELECT client_name FROM clients')
            clients = [row[0] for row in c.fetchall()]
            c.execute('SELECT product_name FROM products')
            products = [row[0] for row in c.fetchall()]
            conn.close()
            error = f"Client '{client_name}' not found. Please select a client from the list."
            return render_template('invoice.html', error=error, clients=clients, products=products, client_name=client_name, turf_type=turf_type, area=area_val, payment_status=payment_status, gst='yes' if gst else '', summary=None)

        client_id = client_row[0]
        import json
        extras_json = json.dumps(extras_details)

        # Save invoice to database with sequential ID
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"DEBUG: Creating invoice with date: {current_date}")
        
        # Find the next available sequential ID starting from 1 - GLOBAL for all users
        c.execute('SELECT id FROM invoices ORDER BY id')
        existing_ids = [row[0] for row in c.fetchall()]
        
        # Find the first gap or next number
        next_id = 1
        for existing_id in existing_ids:
            if existing_id == next_id:
                next_id += 1
            else:
                break
        
        print(f"DEBUG: Assigning global invoice ID: {next_id}")
        
        c.execute('''INSERT INTO invoices (id, client_id, product, quantity, price, gst, total, status, created_date, extras_json, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (next_id, client_id, turf_type, area_val, price, gst_amount, total_price, payment_status, current_date, extras_json, session['user_id']))
        conn.commit()

        # Fetch updated invoices - ALL INVOICES
        c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
                      invoices.gst, invoices.total, invoices.status, invoices.created_date
                      FROM invoices
                      LEFT JOIN clients ON invoices.client_id = clients.id
                      ORDER BY invoices.id ASC''')
        invoices = c.fetchall()
        conn.close()

        return render_template('invoice.html', invoices=invoices, summary={
            'client_name': client_name,
            'turf_type': turf_type,
            'area': area_val,
            'extras_cost': extras_cost,
            'gst': gst_amount,
            'total_price': total_price
        })

    # For GET request, fetch ALL invoices
    c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
                  invoices.gst, invoices.total, invoices.status, invoices.created_date
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  ORDER BY invoices.id ASC''')
    invoices = c.fetchall()
    
    conn.close()
    return render_template('invoice.html', clients=clients, products=products, price_table=price_table, invoices=invoices)

@app.route('/products_list', methods=['GET', 'POST'])
def products_list():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('products_list'):
        return redirect(url_for('access_restricted'))
    import json
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Handle grouped/edited price and stock updates
    if request.method == 'POST':
        # Bamboo products
        bamboo_2m_stock = request.form.get('bamboo_2m_stock', type=int)
        bamboo_2m_price = request.form.get('bamboo_2m_price', type=float)
        bamboo_24m_stock = request.form.get('bamboo_24m_stock', type=int)
        bamboo_24m_price = request.form.get('bamboo_24m_price', type=float)
        bamboo_18m_stock = request.form.get('bamboo_18m_stock', type=int)
        bamboo_18m_price = request.form.get('bamboo_18m_price', type=float)
        
        # Pebbles
        pebbles_black_stock = request.form.get('pebbles_black_stock', type=int)
        pebbles_black_price = request.form.get('pebbles_black_price', type=float)
        pebbles_white_stock = request.form.get('pebbles_white_stock', type=int)
        pebbles_white_price = request.form.get('pebbles_white_price', type=float)
        
        # Fountain
        fountain_stock = request.form.get('fountain_stock', type=int)
        fountain_price = request.form.get('fountain_price')  # custom, can be text
        
        # Turf products
        premium_stock = request.form.get('premium_stock', type=int)
        premium_price = request.form.get('premium_price', type=float)
        green_lush_stock = request.form.get('green_lush_stock', type=int)
        green_lush_price = request.form.get('green_lush_price', type=float)
        natural_40mm_stock = request.form.get('natural_40mm_stock', type=int)
        natural_40mm_price = request.form.get('natural_40mm_price', type=float)
        golf_turf_stock = request.form.get('golf_turf_stock', type=int)
        golf_turf_price = request.form.get('golf_turf_price', type=float)
        imperial_lush_stock = request.form.get('imperial_lush_stock', type=int)
        imperial_lush_price = request.form.get('imperial_lush_price', type=float)
        
        # Other products
        pegs_stock = request.form.get('pegs_stock', type=int)
        pegs_price = request.form.get('pegs_price', type=float)
        artificial_hedges_stock = request.form.get('artificial_hedges_stock', type=int)
        artificial_hedges_price = request.form.get('artificial_hedges_price', type=float)
        adhesive_tape_stock = request.form.get('adhesive_tape_stock', type=int)
        adhesive_tape_price = request.form.get('adhesive_tape_price', type=float)

        # Update DB for each product
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_2m_stock, bamboo_2m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_24m_stock, bamboo_24m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_18m_stock, bamboo_18m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pebbles_black_stock, pebbles_black_price, 'Black Pebbles'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pebbles_white_stock, pebbles_white_price, 'White Pebbles'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (fountain_stock, fountain_price, 'Fountains'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (premium_stock, premium_price, 'Golden Premium Turf'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (green_lush_stock, green_lush_price, 'Golden Green Lush'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (natural_40mm_stock, natural_40mm_price, 'Golden Natural 40mm'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (golf_turf_stock, golf_turf_price, 'Golden Golf Turf'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (imperial_lush_stock, imperial_lush_price, 'Golden Imperial Lush'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pegs_stock, pegs_price, 'Peg (U-pins/Nails)'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (artificial_hedges_stock, artificial_hedges_price, 'Artificial Hedges'))
        # Note: Adhesive Tape doesn't exist in DB, we'll need to add it or skip it
        try:
            c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (adhesive_tape_stock, adhesive_tape_price, 'Adhesive Tape'))
        except:
            pass  # Skip if product doesn't exist
        
        conn.commit()
        # Add success message
        flash('Product prices and stock updated successfully!', 'success')
        # Redirect to avoid resubmission on page refresh
        return redirect(url_for('products_list'))

    c.execute('SELECT product_name, turf_type, description, stock, price, image_url, image_urls FROM products')
    rows = c.fetchall()
    conn.close()

    # Extract specific product values for template variables
    bamboo_products = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_2m_stock = bamboo_products[3] if bamboo_products else 0
    bamboo_2m_price = bamboo_products[4] if bamboo_products else 40.00

    bamboo_24m = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_24m_stock = bamboo_24m[3] if bamboo_24m else 0
    bamboo_24m_price = bamboo_24m[4] if bamboo_24m else 38.00

    bamboo_18m = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_18m_stock = bamboo_18m[3] if bamboo_18m else 0
    bamboo_18m_price = bamboo_18m[4] if bamboo_18m else 38.00

    pebbles_black = next((row for row in rows if row[0] == 'Black Pebbles'), None)
    pebbles_black_stock = pebbles_black[3] if pebbles_black else 0
    pebbles_black_price = pebbles_black[4] if pebbles_black else 18.00

    pebbles_white = next((row for row in rows if row[0] == 'White Pebbles'), None)
    pebbles_white_stock = pebbles_white[3] if pebbles_white else 0
    pebbles_white_price = pebbles_white[4] if pebbles_white else 15.00

    fountain = next((row for row in rows if row[0] == 'Fountains'), None)
    fountain_stock = fountain[3] if fountain else 0
    fountain_price = fountain[4] if fountain else 'Custom'

    # Add missing product variables
    premium = next((row for row in rows if row[0] == 'Golden Premium Turf'), None)
    premium_stock = premium[3] if premium else 50
    premium_price = premium[4] if premium else 45.00

    green_lush = next((row for row in rows if row[0] == 'Golden Green Lush'), None)
    green_lush_stock = green_lush[3] if green_lush else 50
    green_lush_price = green_lush[4] if green_lush else 42.00

    natural_40mm = next((row for row in rows if row[0] == 'Golden Natural 40mm'), None)
    natural_40mm_stock = natural_40mm[3] if natural_40mm else 50
    natural_40mm_price = natural_40mm[4] if natural_40mm else 40.00

    golf_turf = next((row for row in rows if row[0] == 'Golden Golf Turf'), None)
    golf_turf_stock = golf_turf[3] if golf_turf else 30
    golf_turf_price = golf_turf[4] if golf_turf else 55.00

    imperial_lush = next((row for row in rows if row[0] == 'Golden Imperial Lush'), None)
    imperial_lush_stock = imperial_lush[3] if imperial_lush else 40
    imperial_lush_price = imperial_lush[4] if imperial_lush else 48.00

    pegs = next((row for row in rows if row[0] == 'Peg (U-pins/Nails)'), None)
    pegs_stock = pegs[3] if pegs else 200
    pegs_price = pegs[4] if pegs else 20.00

    artificial_hedges = next((row for row in rows if row[0] == 'Artificial Hedges'), None)
    artificial_hedges_stock = artificial_hedges[3] if artificial_hedges else 25
    artificial_hedges_price = artificial_hedges[4] if artificial_hedges else 60.00

    # Adhesive Tape doesn't exist in DB, use defaults
    adhesive_tape_stock = 50
    adhesive_tape_price = 25.00

    # Restore all product image lists
    imperial_lush_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/07/Description-premium-photo-.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/PREMIUM_15-1536x1152.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/FB_IMG_1596714611957.jpg'
    ]
    green_lush_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/04/lush-green.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush5.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush4.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/lush6-1.jpg'
    ]
    natural_40mm_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/natural.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Natural_4.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Natural_1-1152x1536.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/IMG-20191221-WA0026.jpg'
    ]
    golf_turf_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/home_golf_court_golf_carpet-8.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/selected-golf_carpet_golf_putting_green-11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-2-1536x864.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-6.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-9-1536x864.jpg'
    ]
    premium_turf_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/premium.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/Description-premium-photo-.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/PREMIUM_15-1536x1152.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/FB_IMG_1596714611957.jpg'
    ]
    artificial_hedges_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/07/1-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155406.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155305.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/image7.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155421.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-04-at-3.42.28-AM.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-10-at-4.09.19-PM-1152x1536.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-10-at-4.09.18-PM-1152x1536.jpeg'
    ]
    fountain_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/fountain1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210305-WA0041.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0043.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155305.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/p-fountain-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0041.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/fountain-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0031.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0032.jpg'
    ]
    bamboo_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/bamboo13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/bamboo555.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/bamboo-wall1-1536x1024.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/131962086_2195562777243324_1164272107425441220_n.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/6.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/received_521798048828349-1152x1536.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20191120-WA0034.jpg'
    ]
    peg_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/peg2.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/7130I8TfLkL._SL1000_.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/DIY2-768x1024-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/Is-Artificial-Grass-Toxic-QA2-802551536.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/maxresdefault.jpg'
    ]
    tape_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/a-tape2.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210228-WA0034.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/7130I8TfLkL._SL1000_.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/Tape.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/maxresdefault.jpg'
    ]
    pebbles_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/glowing-pebble1-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/pebbles600x600.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/8.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/12.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/received_410804926973400-e1628237434738.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-04-at-18.35.25.jpeg'
    ]

    products = []
    pebbles = None
    for row in rows:
        image_urls = []
        if row[6]:
            try:
                image_urls = json.loads(row[6])
            except Exception:
                image_urls = []
        if not image_urls and row[5]:
            image_urls = [row[5]]

        # Main turf products
        if row[0] == 'Golden Imperial Lush':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': imperial_lush_images
            })
        elif row[0] == 'Golden Green Lush':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': green_lush_images
            })
        elif row[0] == 'Golden Natural 40mm':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': natural_40mm_images
            })
        elif row[0] == 'Golden Golf Turf':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': golf_turf_images
            })
        elif row[0] == 'Golden Premium Turf':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': premium_turf_images
            })
        # Accessories/extras: always use correct multi-image list
        elif row[0] == 'Artificial Hedges':
            products.append({
                'product_name': 'Artificial Hedges (per 50cm x 50cm)',
                'turf_type': '',
                'description': 'Artificial Hedges',
                'stock': row[3],
                'price': 10.0,
                'image_urls': artificial_hedges_images
            })
        elif row[0] == 'Fountain':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': 0,
                'image_urls': fountain_images
            })
        elif row[0] == 'Bamboo':
            # Add all bamboo sizes as separate products
            products.append({
                'product_name': 'Bamboo (2m)',
                'turf_type': '',
                'description': 'Bamboo 2 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
            products.append({
                'product_name': 'Bamboo (2.4m)',
                'turf_type': '',
                'description': 'Bamboo 2.4 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
            products.append({
                'product_name': 'Bamboo (1.8m)',
                'turf_type': '',
                'description': 'Bamboo 1.8 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
        elif row[0] == 'Peg (U-Pins/Nails)':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': peg_images
            })
        elif row[0] == 'Adhesive Joining Tape':
            products.append({
                'product_name': 'Adhesive Joining Tape (15m)',
                'turf_type': '',
                'description': 'Adhesive Joining Tape',
                'stock': row[3],
                'price': 25.0,
                'image_urls': tape_images
            })
        elif row[0] == 'Black Pebbles':
            products.append({
                'product_name': 'Black Pebbles (20kg bag)',
                'turf_type': '',
                'description': 'Black Decorative Pebbles',
                'stock': row[3],
                'price': 18.0,
                'image_urls': pebbles_images
            })
        elif row[0] == 'White Pebbles':
            products.append({
                'product_name': 'White Pebbles (20kg bag)',
                'turf_type': '',
                'description': 'White Decorative Pebbles',
                'stock': row[3],
                'price': 15.0,
                'image_urls': pebbles_images
            })
        else:
            # For any other product, fallback to DB images
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': image_urls
            })
    return render_template('products_list.html', 
                           products=rows,
                           bamboo_2m_stock=bamboo_2m_stock,
                           bamboo_2m_price=bamboo_2m_price,
                           bamboo_24m_stock=bamboo_24m_stock,
                           bamboo_24m_price=bamboo_24m_price,
                           bamboo_18m_stock=bamboo_18m_stock,
                           bamboo_18m_price=bamboo_18m_price,
                           pebbles_black_stock=pebbles_black_stock,
                           pebbles_black_price=pebbles_black_price,
                           pebbles_white_stock=pebbles_white_stock,
                           pebbles_white_price=pebbles_white_price,
                           fountain_stock=fountain_stock,
                           fountain_price=fountain_price,
                           premium_stock=premium_stock,
                           premium_price=premium_price,
                           green_lush_stock=green_lush_stock,
                           green_lush_price=green_lush_price,
                           natural_40mm_stock=natural_40mm_stock,
                           natural_40mm_price=natural_40mm_price,
                           golf_turf_stock=golf_turf_stock,
                           golf_turf_price=golf_turf_price,
                           imperial_lush_stock=imperial_lush_stock,
                           imperial_lush_price=imperial_lush_price,
                           pegs_stock=pegs_stock,
                           pegs_price=pegs_price,
                           artificial_hedges_stock=artificial_hedges_stock,
                           artificial_hedges_price=artificial_hedges_price,
                           adhesive_tape_stock=adhesive_tape_stock,
                           adhesive_tape_price=adhesive_tape_price,
                           bamboo_images=bamboo_images,
                           pebbles_images=pebbles_images,
                           fountain_images=fountain_images,
                           imperial_lush_images=imperial_lush_images,
                           green_lush_images=green_lush_images,
                           natural_40mm_images=natural_40mm_images,
                           golf_turf_images=golf_turf_images,
                           premium_turf_images=premium_turf_images,
                           artificial_hedges_images=artificial_hedges_images,
                           peg_images=peg_images,
                           tape_images=tape_images)

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('quotes'):
        return redirect(url_for('access_restricted'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))


    if request.method == 'POST':
        # Handle form submission
        client_name = request.form.get('client_name')
        turf_type = request.form.get('turf_type')
        area_in_sqm_str = request.form.get('area_in_sqm')
        other_products = request.form.get('other_products')
        pebbles_custom_type = request.form.get('pebbles_custom_type')
        pebbles_qty = request.form.get('pebbles_qty', type=int)
        other_product_quantity = request.form.get('other_product_quantity', type=int)
        custom_price = request.form.get('custom_price', type=float)

        # Calculate total price
        # Fetch all product prices from DB for dynamic pricing
        c = sqlite3.connect('users.db').cursor()
        c.execute('SELECT product_name, price FROM products')
        price_table = {}
        for row in c.fetchall():
            try:
                price_table[row[0]] = float(row[1]) if row[1] else 0.0
            except (ValueError, TypeError):
                # Handle non-numeric prices like "Custom"
                price_table[row[0]] = 0.0

        try:
            area_in_sqm = float(area_in_sqm_str) if area_in_sqm_str else 0.0
        except ValueError:
            area_in_sqm = 0.0

        base_price = price_table.get(turf_type, 0) * area_in_sqm
        other_product_price = 0
        other_products_display = other_products
        if other_products == 'Fountain':
            other_product_price = custom_price or 0
        elif other_products == 'Pebbles':
            if pebbles_custom_type and pebbles_custom_type.lower() in ['multicolour', 'glow']:
                pebble_price = price_table.get('Pebbles Multicolour/Glow', 0)
            else:
                pebble_price = price_table.get('Pebbles Standard', 0)
            other_product_price = (pebble_price if pebbles_qty else 0) * (pebbles_qty or 0)
            other_products_display = f"Pebbles ({pebbles_custom_type}): {pebbles_qty}"
        elif other_products:
            other_product_price = price_table.get(other_products, 0) * (other_product_quantity or 0)

        total_price = base_price + other_product_price

        # Store in database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO quotes (client_name, turf_type, area_in_sqm, other_products, total_price, owner_id)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                         (client_name, turf_type, area_in_sqm, other_products_display, total_price, user_id))
            conn.commit()
            print(f"Quote saved: {client_name}, {turf_type}, {area_in_sqm}, {other_products_display}, {total_price}, {user_id}")
        except Exception as e:
            print(f"Error saving quote: {e}")
        # Fetch all quotes for this user
        c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
        quotes = c.fetchall()
        conn.close()

        summary = {
            'client_name': client_name,
            'turf_type': turf_type,
            'area_in_sqm': area_in_sqm,
            'other_products': other_products_display or 'None',
            'total_price': total_price
        }
        # Also fetch for payments page
        # No redirect, just render as before
        return render_template('quotes.html', success=True, quotes=quotes, summary=summary)

    # For GET or if not POST, just show all quotes
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
    quotes = c.fetchall()
    conn.close()
    return render_template('quotes.html', quotes=quotes)
@app.route('/payments')
def payments():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    import json

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Get invoices data for payments including extras_json - SHOW ALL INVOICES
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date,
                  invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.extras_json
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  ORDER BY invoices.id ASC''')
    invoices_data = c.fetchall()

    # Debug: Let's see what invoices exist
    print(f"DEBUG - Payments page for user {session.get('user_name')}:")
    print(f"  Found {len(invoices_data)} invoices total")
    if invoices_data:
        print(f"  First invoice: {invoices_data[0]}")
        statuses = [inv[2] for inv in invoices_data]
        print(f"  Invoice statuses: {statuses}")
        totals = [inv[8] for inv in invoices_data if inv[8]]
        print(f"  Invoice totals: {totals}")
        print(f"  Sum of all totals: {sum(float(t) for t in totals if t)}")

    # Get clients data
    c.execute('SELECT * FROM clients')  # Removed owner_id restriction - all users see all clients
    clients_data = c.fetchall()

    # Get quotes data
    c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
    quotes_data = c.fetchall()

    conn.close()

    # Format the data for the template
    invoices = []
    for invoice in invoices_data:
        status = invoice[2]
        # Parse extras_json
        extras = {}
        if invoice[9]:
            try:
                extras = json.loads(invoice[9])
            except json.JSONDecodeError:
                extras = {}

        invoices.append({
            'id': invoice[0],
            'client_name': invoice[1],
            'status': status,
            'due_date': invoice[3],
            'product': invoice[4],
            'quantity': invoice[5],
            'price': float(invoice[6]) if invoice[6] else 0.0,
            'gst': float(invoice[7]) if invoice[7] else 0.0,
            'total': float(invoice[8]) if invoice[8] else 0.0,
            'extras': extras
        })

    # Format clients data
    clients = []
    for client in clients_data:
        clients.append({
            'id': client[0],
            'client_name': client[1],
            'email': client[2] or '',
            'phone': client[3] or '',
            'account_type': client[4] or '',
            'company_name': client[5] or '',
            'actions': client[6] or ''
        })

    # Format quotes data
    quotes = []
    for quote in quotes_data:
        quotes.append({
            'id': quote[0],
            'client_name': quote[1],
            'turf_type': quote[2],
            'area_in_sqm': quote[3],
            'other_products': quote[4] or 'None',
            'total_price': float(quote[5]) if quote[5] else 0.0
        })

    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('payments.html', invoices=invoices, clients=clients, quotes=quotes, current_date=current_date)

@app.route('/calendar')
def calendar():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('calendar'):
        return redirect(url_for('access_restricted'))

    # Get current date for calendar navigation
    actual_today = datetime.now().date()
    current_year = request.args.get('year', actual_today.year, type=int)
    current_month = request.args.get('month', actual_today.month, type=int)
    current_day = request.args.get('day', actual_today.day, type=int)
    view = request.args.get('view', 'month')

    # Create current date object
    current_date = datetime(current_year, current_month, current_day)

    # Fetch tasks from the database for the calendar view
    tasks = get_all_tasks()

    # Map task statuses to colors
    status_colors = {
        'Not completed': 'red',
        'In Progress': 'orange',
        'Completed': 'green'
    }

    # Organize tasks by date
    tasks_by_date = {}
    for task in tasks:
        task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
        task_color = status_colors.get(task[7], 'gray')  # task[7] is status
        task = list(task)
        task.append(task_color)  # task[9] = color
        if task_date not in tasks_by_date:
            tasks_by_date[task_date] = []
        tasks_by_date[task_date].append(task)

    # Prepare data for rendering based on view
    calendar_data = []
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    full_day_tasks = []

    if view == 'month':
        cal = Calendar(firstweekday=6)  # Set Sunday as the first day of the week
        days = cal.itermonthdays(current_year, current_month)
        # Adjust today to current_date for consistency with navigation
        today = current_date.date()
        for day in days:
            if day == 0:
                calendar_data.append({'day': None, 'tasks': [], 'is_today': False})
            else:
                date = datetime(current_year, current_month, day).date()
                is_today = (date == today)
                calendar_data.append({'day': day, 'tasks': tasks_by_date.get(date, []), 'is_today': is_today})
        header_text = month_names[current_month - 1]
    elif view == 'week':
        # Fix weekly view to start on Sunday and show correct tasks
        # Python's weekday(): Monday=0, Sunday=6
        weekday = current_date.weekday()
        # Calculate days to subtract to get to Sunday (weekday 6)
        days_to_sunday = (weekday + 1) % 7
        start_of_week = current_date - timedelta(days=days_to_sunday)
        end_of_week = start_of_week + timedelta(days=6)
        for i in range(7):
            date = start_of_week + timedelta(days=i)
            is_today = (date.date() == actual_today)
            calendar_data.append({'day': date.day, 'tasks': tasks_by_date.get(date.date(), []), 'is_today': is_today})
        start_suffix = 'th' if 11 <= start_of_week.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(start_of_week.day % 10, 'th')
        end_suffix = 'th' if 11 <= end_of_week.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(end_of_week.day % 10, 'th')
        if start_of_week.month == end_of_week.month and start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix} - {end_of_week.day}{end_suffix})"
        elif start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
        else:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
    elif view == 'day':
        tasks_by_hour = {hour: [] for hour in range(24)}
        full_day_tasks = []
        for task in tasks_by_date.get(current_date.date(), []):
            if task[4]:  # task_time
                try:
                    hour = int(task[4].split(':')[0])
                    tasks_by_hour[hour].append(task)
                except ValueError:
                    pass
            else:
                full_day_tasks.append(task)
        calendar_data = [{'hour': 'All Day', 'tasks': full_day_tasks}] + [{'hour': hour, 'tasks': tasks_by_hour[hour]} for hour in range(24)]
        # Fix the day view header to show correct day of week for the current_date
        day_of_week = current_date.strftime('%A')
        header_text = f"{month_names[current_month - 1]} {current_day} ({day_of_week})"
        current_date_str = current_date.strftime('%Y-%m-%d')

    # Fetch all users for assignment dropdown
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM users ORDER BY name')
    users = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return render_template('calendar.html',
                           calendar_data=calendar_data,
                           current_year=current_year,
                           current_month=current_month,
                           current_day=current_day,
                           header_text=header_text,
                           month_names=month_names,
                           view=view,
                           tasks=tasks,
                           full_day_tasks=full_day_tasks,
                           current_date=current_date_str if view == 'day' else None,
                           users=users)



@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        account_type = request.form.get('account_type', '')
        company_name = request.form.get('company_name', '')
        email = request.form.get('email', '')
        actions = request.form.get('actions', '').strip()

        # Validate input
        import re
        if not re.match(r'^[A-Za-z ]+$', contact_name):
            conn.close()
            return render_template('edit_client.html', error='Contact name must contain only alphabetic characters and spaces.', client=client)
        if phone_number and not phone_number.isdigit():
            conn.close()
            return render_template('edit_client.html', error='Phone number must contain digits only.', client=client)
        if account_type not in ['Active', 'Deactivated']:
            conn.close()
            return render_template('edit_client.html', error='Invalid account type.', client=client)
        if '@' not in email or '.' not in email:
            conn.close()
            return render_template('edit_client.html', error='Invalid email format.', client=client)

        # Update client in database
        c.execute('''UPDATE clients SET client_name=?, phone=?, account_type=?, company_name=?, email=?, actions=? WHERE id=?''',
                  (contact_name, phone_number, account_type, company_name, email, actions, client_id))
        conn.commit()
        conn.close()

        # Redirect to clients and invoices list with clients tab active
        return redirect(url_for('payments') + '#clients')

    c.execute('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ?', (client_id,))
    client = c.fetchone()
    conn.close()

    if not client:
        return render_template('edit_client.html', error="Client not found.")

    return render_template('edit_client.html', client=client)

# Task management API endpoints
@app.route('/api/tasks', methods=['GET'])
def get_all_tasks_api():
    if 'user_name' not in session:
        print("Unauthorized access attempt to get tasks.")
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks ORDER BY task_date, task_time')
    tasks = c.fetchall()
    conn.close()

    print(f"Retrieved {len(tasks)} tasks from database")
    if tasks:
        print("Tasks found:")
        for task in tasks:
            print(f"  - ID: {task[0]}, Title: {task[1]}, Date: {task[3]}")

    # Convert to list of dictionaries
    task_list = []
    for task in tasks:
        task_list.append({
            'id': task[0],
            'title': task[1],
            'description': task[2],
            'date': task[3],
            'time': task[4],
            'end_time': task[5],
            'location': task[6],
            'status': task[7],
            'created_at': task[8],
            'assigned_user_id': task[9] if len(task) > 9 else None
       
        })

    return jsonify(task_list)

@app.route('/api/tasks', methods=['POST'], endpoint='add_task_api')
def add_task():
    if 'user_name' not in session:
        print("Unauthorized access attempt to add task.")
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    print(f"Received task data: {data}")

    title = data.get('title')
    description = data.get('description', '')
    task_date = data.get('date')
    task_time = data.get('time', '')
    task_end_time = data.get('end_time', '')
    location = data.get('location', '')
    status = data.get('status', 'Not completed')
    assigned_user_id = data.get('assigned_user_id')
    owner_id = session.get('user_id')

    if not title or not task_date:
        print("Task creation failed: Title and date are required.")
        return jsonify({'error': 'Title and date are required'}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id if assigned_user_id else None, owner_id))
        task_id = c.lastrowid  # Get the ID of the newly added task
        conn.commit()
        print(f"Task added successfully: {title} with ID {task_id}.")
        conn.close()
        return jsonify({'message': 'Task added successfully', 'task_id': task_id}), 201
    except Exception as e:
        print(f"Error adding task: {str(e)}")
        conn.close()
        return jsonify({'error': 'Failed to add task'}), 500
@app.route('/api/users')
def api_users():
    if 'user_name' not in session:
        return jsonify([])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name, role FROM users ORDER BY name')
    users = [{'id': row[0], 'name': row[1], 'role': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    conn.close()

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify({
        'id': task[0],
        'title': task[1],
        'description': task[2],
        'date': task[3],
        'time': task[4],
        'end_time': task[5],
        'location': task[6],
        'status': task[7],
        'created_at': task[8]
    })

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    task_date = data.get('date')
    task_time = data.get('time', '')
    task_end_time = data.get('end_time', '')
    location = data.get('location', '')
    status = data.get('status', 'Not completed')
    assigned_user_id = data.get('assigned_user_id')

    if not title or not task_date:
        return jsonify({'error': 'Title and date are required'}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''UPDATE tasks SET title=?, description=?, task_date=?, task_time=?, task_end_time=?, location=?, status=?, assigned_user_id=?
                 WHERE id=?''',
                 (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, task_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Task updated successfully'})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()

    # Reset Account ID to 1 if no other clients exist
    cur = c.execute('SELECT COUNT(*) FROM clients')
    count = cur.fetchone()[0]
    if count == 0:
        # Reset the sqlite_sequence for clients table to 0
        c.execute("DELETE FROM sqlite_sequence WHERE name='clients'")
        conn.commit()

    conn.close()

    return redirect(url_for('payments'))

@app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    # Define price table for products (ensure values are JSON serializable)
    price_table = {
        'Golden Imperial Lush': 45.0,
        'Golden Green Lush': 43.0,
        'Golden Natural 40mm': 47.0,
        'Golden Golf Turf': 50.0,
        'Golden Premium Turf': 52.0
    }

    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        product = request.form.get('product', '').strip()
        quantity = request.form.get('quantity', type=float)
        price = request.form.get('price', type=float)
        gst_checkbox = request.form.get('gst_checkbox') == 'yes'
        status = request.form.get('status', '')

        # Fetch invoice before validation to avoid UnboundLocalError
        c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.status, invoices.created_date
                     FROM invoices
                     LEFT JOIN clients ON invoices.client_id = clients.id
                     WHERE invoices.id = ?''', (invoice_id,))
        invoice = c.fetchone()

        # Validate input
        if not client_name or not product or quantity is None or price is None:
            conn.close()
            return render_template('edit_invoice.html', error='All fields are required.', invoice=invoice, clients=clients, products=products, price_table=price_table)
        if status not in ['Paid', 'Unpaid']:
            conn.close()
            return render_template('edit_invoice.html', error='Invalid status.', invoice=invoice, clients=clients, products=products, price_table=price_table)

        # Calculate GST and total
        gst = price * 0.10 if gst_checkbox else 0
        total = price + gst

        # Get client_id from client_name
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client_row = c.fetchone()
        client_id = client_row[0] if client_row else None

        if not client_id:
            conn.close()
            return render_template('edit_invoice.html', error='Client not found.', invoice=invoice, clients=clients, products=products, price_table=price_table)

        # Update invoice in database
        c.execute('''UPDATE invoices SET client_id=?, product=?, quantity=?, price=?, gst=?, total=?, status=? WHERE id=?''',
                  (client_id, product, quantity, price, gst, total, status, invoice_id))
        conn.commit()
        conn.close()

        # Redirect to payments with invoices tab active
        return redirect(url_for('payments') + '#invoices')

    c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.status, invoices.created_date
                 FROM invoices
                 LEFT JOIN clients ON invoices.client_id = clients.id
                 WHERE invoices.id = ?''', (invoice_id,))
    invoice = c.fetchone()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    conn.close()

    if not invoice:
        return render_template('edit_invoice.html', error="Invoice not found.")

    return render_template('edit_invoice.html', invoice=invoice, clients=clients, products=products, price_table=price_table)

def resequence_invoice_ids():
    """Resequence all invoice IDs to start from 1 with no gaps"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Get all invoices ordered by creation date to maintain chronological order
    c.execute('SELECT * FROM invoices ORDER BY created_date ASC')
    invoices = c.fetchall()
    
    if not invoices:
        conn.close()
        return
    
    print(f"Resequencing {len(invoices)} invoices...")
    
    # Delete all invoices temporarily
    c.execute('DELETE FROM invoices')
    
    # Re-insert with sequential IDs starting from 1
    for index, invoice in enumerate(invoices, start=1):
        old_id = invoice[0]  # Original ID
        # Reconstruct the invoice with new ID (without discount column)
        new_values = (
            index,           # new id
            invoice[1],      # client_id
            invoice[2],      # product
            invoice[3],      # quantity
            invoice[4],      # price
            invoice[5],      # gst
            invoice[6],      # total
            invoice[7],      # status
            invoice[8],      # created_date
            invoice[9],      # extras_json
            invoice[10]      # owner_id
        )
        c.execute('''INSERT INTO invoices (id, client_id, product, quantity, price, gst, total, status, created_date, extras_json, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', new_values)
        print(f"Resequenced invoice: {old_id} -> {index}")
    
    conn.commit()
    conn.close()
    print("Resequencing complete!")

@app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()
    
    # Resequence all IDs after deletion
    resequence_invoice_ids()
    print(f"Deleted invoice {invoice_id} and resequenced all IDs")

    return redirect(url_for('payments'))

@app.route('/quotes/delete/<int:quote_id>', methods=['POST'])
def delete_quote(quote_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('quotes'):
        return redirect(url_for('access_restricted'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM quotes WHERE id = ? AND owner_id = ?', (quote_id, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for('quotes'))

@app.route('/add_task', methods=['POST'], endpoint='add_task_form')
def add_task():
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not has_permission('calendar'):
        return jsonify({'error': 'Access restricted'}), 403
    if 'user_name' not in session:
        return redirect(url_for('login'))

    title = request.form.get('title')
    description = request.form.get('description')
    task_date = request.form.get('task_date')
    task_time = request.form.get('task_time')
    task_end_time = request.form.get('task_end_time')
    location = request.form.get('location')
    status = request.form.get('status')
    assigned_user_id = request.form.get('assigned_user_id')
    owner_id = session.get('user_id')

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id))
    conn.commit()
    conn.close()

    return redirect(url_for('calendar'))

@app.route('/verify_code/<email>', methods=['GET', 'POST'])
def verify_code(email):
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            return render_template('verify_code.html', email=email, error='Please enter the verification code.')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, role, verification_code, token_expiry FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user and user[3] == code and datetime.now().strftime('%Y-%m-%d %H:%M:%S') < user[4]:
            # Successful verification
            # Redirect to reset password page instead of logging in
            return redirect(url_for('reset_password', email=email))
        else:
            return render_template('verify_code.html', email=email, error='Invalid or expired verification code.')

    return render_template('verify_code.html', email=email)

# Update user IDs to overwrite deleted ones
@app.route('/profiles/update_ids', methods=['POST'])
def update_user_ids():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch all users ordered by ID
    c.execute('SELECT id FROM users ORDER BY id')
    users = c.fetchall()

    # Reassign IDs sequentially
    for index, user in enumerate(users, start=1):
        c.execute('UPDATE users SET id = ? WHERE id = ?', (index, user[0]))

    conn.commit()
    conn.close()

    flash('User IDs updated successfully!')
    return redirect(url_for('profiles'))

if __name__ == "__main__":
    app.run(debug=True)