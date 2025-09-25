from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, bcrypt, os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-for-golden-turf-2024'

# Template helper function for permission checking
@app.template_global()
def user_has_permission(module):
    if 'user_id' not in session: return False
    if session['user_id'] == 1: return True  # ID 1 always has access
    user_permissions = session.get('user_permissions', '')
    return module in (user_permissions or '').split(',')

# Helper function to determine if user should see all data or just their own
def should_see_all_data():
    if 'user_id' not in session: return False
    if session['user_id'] == 1: return True  # ID 1 sees all data
    user_role = session.get('user_role', '')
    return user_role == 'admin'  # Admin users see all data

# Helper function to determine if user should see all data for a specific module
def should_see_all_data_for_module(module):
    if 'user_id' not in session: return False
    if session['user_id'] == 1: return True  # ID 1 sees all data
    user_role = session.get('user_role', '')
    if user_role == 'admin': return True  # Admin users see all data
    # Users with specific permissions see all data for that module
    user_permissions = session.get('user_permissions', '')
    return module in (user_permissions or '').split(',')

# Helper function to get data query based on user permissions for specific module
def get_data_filter_for_module(module):
    if should_see_all_data_for_module(module):
        return ('', ())  # No owner filter - see all data
    else:
        return ('WHERE owner_id = ?', (session['user_id'],))  # Filter by owner

# Helper function to get data query based on user permissions (general)
def get_data_filter():
    if should_see_all_data():
        return ('', ())  # No owner filter - see all data
    else:
        return ('WHERE owner_id = ?', (session['user_id'],))  # Filter by owner

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, password = request.form.get('name', '').strip(), request.form.get('email', '').strip(), request.form.get('password', '').strip()
        if db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one'):
            flash('Email already registered')
        else:
            hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            db_exec('INSERT INTO users (name, email, password_hash, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, hash_pw, 'user', 'dashboard'))
            
            # Check if this user got ID 1 - if so, make them admin automatically
            new_user = db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one')
            if new_user and new_user[0] == 1:
                db_exec('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                       ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', 1))
                flash('Registration successful! You have been granted admin access as the first user.')
            else:
                flash('Registration successful')
            return redirect(url_for('login'))
    return render_template('register.html')
# Database utilities
def db_exec(query, params=(), fetch=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute(query, params)
    if fetch == 'one': result = c.fetchone()
    elif fetch == 'all': result = c.fetchall()
    else: result = None
    conn.commit()
    conn.close()
    return result

def reorganize_user_ids():
    users = db_exec('SELECT id FROM users ORDER BY id', fetch='all')
    for new_id, (old_id,) in enumerate(users, 1):
        if new_id != old_id:
            db_exec('UPDATE users SET id = ? WHERE id = ?', (new_id, old_id))
    db_exec("DELETE FROM sqlite_sequence WHERE name='users'")
    if users: db_exec("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (len(users),))

def reset_clients_ids():
    """Reset client IDs to start from 1 and fill gaps"""
    clients = db_exec('SELECT id FROM clients ORDER BY id', fetch='all')
    for new_id, (old_id,) in enumerate(clients, 1):
        if new_id != old_id:
            db_exec('UPDATE clients SET id = ? WHERE id = ?', (new_id, old_id))
    db_exec("DELETE FROM sqlite_sequence WHERE name='clients'")
    if clients: 
        db_exec("INSERT INTO sqlite_sequence (name, seq) VALUES ('clients', ?)", (len(clients),))
    else:
        db_exec("INSERT INTO sqlite_sequence (name, seq) VALUES ('clients', 0)")

def reset_invoices_ids():
    """Reset invoice IDs to start from 1 and fill gaps"""
    invoices = db_exec('SELECT id FROM invoices ORDER BY id', fetch='all')
    for new_id, (old_id,) in enumerate(invoices, 1):
        if new_id != old_id:
            db_exec('UPDATE invoices SET id = ? WHERE id = ?', (new_id, old_id))
    db_exec("DELETE FROM sqlite_sequence WHERE name='invoices'")
    if invoices: 
        db_exec("INSERT INTO sqlite_sequence (name, seq) VALUES ('invoices', ?)", (len(invoices),))
    else:
        db_exec("INSERT INTO sqlite_sequence (name, seq) VALUES ('invoices', 0)")

def has_permission(module):
    if 'user_id' not in session: return False
    
    # ID 1 users always have full access to everything
    if session['user_id'] == 1:
        return True
    
    user = db_exec('SELECT permissions FROM users WHERE id = ?', (session['user_id'],), 'one')
    return user and module in (user[0] or '').split(',')

def migrate_users_table():
    # Migration has already been completed - just ensure columns exist
    try: db_exec('ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT "dashboard"')
    except: pass
    try: db_exec('ALTER TABLE users ADD COLUMN password_hash BLOB')
    except: pass
    # Ensure first user is admin
    first = db_exec('SELECT id FROM users ORDER BY id LIMIT 1', fetch='one')
    if first: db_exec("UPDATE users SET role = ?, permissions = ? WHERE id = ?", ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first[0]))

def ensure_admin_exists():
    # Always ensure ID 1 is admin if it exists
    user_id_1 = db_exec('SELECT id, role FROM users WHERE id = 1', fetch='one')
    if user_id_1:
        if user_id_1[1] != 'admin':
            print("Making user ID 1 admin (required for system security)...")
            db_exec('UPDATE users SET role = ?, permissions = ? WHERE id = 1', 
                   ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles'))
            print("User ID 1 granted admin access!")
        else:
            print("User ID 1 already has admin access")
    else:
        # If no user ID 1 exists, check if any admin exists
        admin_exists = db_exec('SELECT id FROM users WHERE role = "admin"', fetch='one')
        if not admin_exists:
            # Get the first user by ID and make them admin
            first_user = db_exec('SELECT id FROM users ORDER BY id LIMIT 1', fetch='one')
            if first_user:
                print(f"Setting user ID {first_user[0]} as admin...")
                db_exec('UPDATE users SET role = ?, permissions = ? WHERE id = ?', 
                       ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first_user[0]))
                print("Admin role assigned successfully!")
            reorganize_user_ids()

def authenticate_user(email, password):
    user = db_exec('SELECT id, name, password_hash, permissions, role FROM users WHERE email = ?', (email,), 'one')
    if not user: return None
    # Check password_hash 
    if user[2] and bcrypt.checkpw(password.encode('utf-8'), user[2]):
        return user
    # Default password fallback for users without password_hash
    elif user[2] is None and password == 'Password123':
        new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db_exec('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user[0]))
        return user
    return None

def create_tasks_table():
    try: 
        db_exec('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            title TEXT NOT NULL, 
            description TEXT, 
            task_date TEXT NOT NULL, 
            task_time TEXT, 
            task_end_time TEXT, 
            location TEXT, 
            status TEXT DEFAULT 'Not completed', 
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, 
            owner_id INTEGER,
            assigned_user_id INTEGER
        )''')
    except: pass

def create_clients_table():
    try: db_exec('''CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT NOT NULL, email TEXT, phone TEXT, account_type TEXT, company_name TEXT, actions TEXT, created_date TEXT, owner_id INTEGER)''')
    except: pass

def create_invoices_table():
    try: 
        db_exec('''CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            turf_type TEXT,
            area REAL,
            payment_status TEXT,
            gst REAL DEFAULT 0,
            subtotal REAL DEFAULT 0,
            total REAL DEFAULT 0,
            extras TEXT,
            created_date TEXT,
            due_date TEXT,
            owner_id INTEGER,
            artificial_hedges_qty INTEGER DEFAULT 0,
            fountain_price REAL DEFAULT 0,
            bamboo_products_size TEXT,
            bamboo_products_qty INTEGER DEFAULT 0,
            pebbles_custom_type TEXT,
            pebbles_qty INTEGER DEFAULT 0,
            pegs_qty INTEGER DEFAULT 0,
            adhesive_tape_qty INTEGER DEFAULT 0
        )''')
    except: pass

def fix_clients_table_constraints():
    """Remove the problematic UNIQUE constraint on client_name"""
    try:
        # Check if the constraint exists
        result = db_exec("SELECT sql FROM sqlite_master WHERE type='table' AND name='clients'", fetch='one')
        if result and 'UNIQUE(client_name)' in result[0]:
            # Create a new table without the constraint
            db_exec('''CREATE TABLE IF NOT EXISTS clients_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                account_type TEXT,
                company_name TEXT,
                actions TEXT,
                created_date TEXT,
                owner_id INTEGER
            )''')
            
            # Copy data from old table to new table
            db_exec('INSERT INTO clients_new SELECT * FROM clients')
            
            # Drop old table and rename new table
            db_exec('DROP TABLE clients')
            db_exec('ALTER TABLE clients_new RENAME TO clients')
            
            print("Fixed clients table constraints - removed UNIQUE constraint on client_name")
    except Exception as e:
        print(f"Note: Could not fix clients table constraints: {e}")
        pass

def migrate_tasks_table():
    try: db_exec('ALTER TABLE tasks ADD COLUMN assigned_user_id INTEGER')
    except: pass

def get_all_tasks(user_id=None):
    # Get tasks owned by the current session user
    session_user_id = session.get('user_id')
    if not session_user_id:
        return []
    
    if user_id:
        # Filter by assigned user but still respect ownership
        query = 'SELECT * FROM tasks WHERE owner_id = ? AND assigned_user_id = ? ORDER BY task_date, task_time'
        params = (session_user_id, user_id)
    else:
        # Get all tasks owned by the current session user
        query = 'SELECT * FROM tasks WHERE owner_id = ? ORDER BY task_date, task_time'
        params = (session_user_id,)
    return db_exec(query, params, 'all') or []

# Initialize database
migrate_users_table()
ensure_admin_exists()
create_tasks_table()
create_clients_table()
create_invoices_table()
fix_clients_table_constraints()
migrate_tasks_table()
# Reset ID sequences to start from 1 and fill gaps
reset_clients_ids()
reset_invoices_ids()

# Routes
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email', '').strip(), request.form.get('password', '').strip()
        user = authenticate_user(email, password)
        if user:
            session.update({'user_id': user[0], 'user_name': user[1], 'user_email': email, 'user_role': user[4], 'user_permissions': user[3]})
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Get data filter based on user permissions for clients
    client_filter_clause, client_params = get_data_filter_for_module('clients')
    
    # Get total clients
    if client_filter_clause:
        total_clients_result = db_exec(f'SELECT COUNT(*) FROM clients {client_filter_clause}', client_params, fetch='one')
    else:
        total_clients_result = db_exec('SELECT COUNT(*) FROM clients', fetch='one')
    total_clients = total_clients_result[0] if total_clients_result else 0
    
    # Get admin users
    admins = db_exec('SELECT id, name, email FROM users WHERE role = "admin" ORDER BY id', fetch='all') or []
    
    # Calculate sales KPIs
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Get data filter for payments/invoices
    payment_filter_clause, payment_params = get_data_filter_for_module('payments')
    
    # Today's sales (only paid invoices)  
    if payment_filter_clause:
        today_sales_result = db_exec(f'SELECT SUM(total) FROM invoices {payment_filter_clause} AND DATE(created_date) = ? AND payment_status = "Paid"', payment_params + (today,), fetch='one')
    else:
        today_sales_result = db_exec('SELECT SUM(total) FROM invoices WHERE DATE(created_date) = ? AND payment_status = "Paid"', (today,), fetch='one')
    today_sales = today_sales_result[0] if today_sales_result and today_sales_result[0] else 0
    
    # Yesterday's sales (only paid invoices)
    if payment_filter_clause:
        yesterday_sales_result = db_exec(f'SELECT SUM(total) FROM invoices {payment_filter_clause} AND DATE(created_date) = ? AND payment_status = "Paid"', payment_params + (yesterday,), fetch='one')
    else:
        yesterday_sales_result = db_exec('SELECT SUM(total) FROM invoices WHERE DATE(created_date) = ? AND payment_status = "Paid"', (yesterday,), fetch='one')
    yesterday_sales = yesterday_sales_result[0] if yesterday_sales_result and yesterday_sales_result[0] else 0
    
    # Last 7 days sales (only paid invoices)
    if payment_filter_clause:
        last_7_days_sales_result = db_exec(f'SELECT SUM(total) FROM invoices {payment_filter_clause} AND DATE(created_date) >= ? AND payment_status = "Paid"', payment_params + (week_ago,), fetch='one')
    else:
        last_7_days_sales_result = db_exec('SELECT SUM(total) FROM invoices WHERE DATE(created_date) >= ? AND payment_status = "Paid"', (week_ago,), fetch='one')
    last_7_days_sales = last_7_days_sales_result[0] if last_7_days_sales_result and last_7_days_sales_result[0] else 0
    
    # Total sales (only paid invoices)
    if payment_filter_clause:
        total_sales_result = db_exec(f'SELECT SUM(total) FROM invoices {payment_filter_clause} AND payment_status = "Paid"', payment_params, fetch='one')
    else:
        total_sales_result = db_exec('SELECT SUM(total) FROM invoices WHERE payment_status = "Paid"', fetch='one')
    total_sales = total_sales_result[0] if total_sales_result and total_sales_result[0] else 0
    
    return render_template('dashboard.html', 
                         total_clients=total_clients, 
                         admins=admins,
                         today_sales=today_sales,
                         yesterday_sales=yesterday_sales,
                         last_7_days_sales=last_7_days_sales,
                         total_sales=total_sales)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    error = success = None
    if request.method == 'POST':
        contact_name, phone_number, account_type, company_name, email, actions = [request.form.get(k, '').strip() for k in ['contact_name', 'phone_number', 'account_type', 'company_name', 'email', 'actions']]
        if not contact_name: error = 'Contact name is required.'
        elif account_type not in ['Active', 'Deactivated']: error = 'Please select a valid account type.'
        elif not email or '@' not in email: error = 'Please enter a valid email address.'
        if not error:
            try:
                # Check if client already exists for this user (to prevent confusion)
                existing = db_exec('SELECT id FROM clients WHERE client_name = ? AND owner_id = ? AND email = ?', (contact_name, session['user_id'], email), 'one')
                if existing:
                    error = f'A client with the name "{contact_name}" and email "{email}" already exists.'
                else:
                    db_exec('INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (contact_name, email, phone_number, account_type, company_name, actions, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['user_id']))
                    success = f'Client "{contact_name}" saved successfully.'
            except Exception as e: error = f'Failed to save client: {str(e)}'
    # Get data based on user permissions for clients
    where_clause, params = get_data_filter_for_module('clients')
    if where_clause:
        client_list = db_exec(f'SELECT * FROM clients {where_clause} ORDER BY id DESC', params, 'all') or []
    else:
        client_list = db_exec('SELECT * FROM clients ORDER BY id DESC', (), 'all') or []
    return render_template('clients.html', clients=client_list, error=error, success=success)

@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    if request.method == 'POST':
        contact_name, phone_number, account_type, company_name, email, actions = [request.form.get(k, '').strip() for k in ['contact_name', 'phone_number', 'account_type', 'company_name', 'email', 'actions']]
        error = None
        if not contact_name: error = 'Contact name is required.'
        elif account_type not in ['Active', 'Deactivated']: error = 'Please select a valid account type.'
        elif not email or '@' not in email: error = 'Please enter a valid email address.'
        if not error:
            db_exec('UPDATE clients SET client_name=?, phone=?, account_type=?, company_name=?, email=?, actions=? WHERE id=? AND owner_id=?', (contact_name, phone_number, account_type, company_name, email, actions, client_id, session['user_id']))
            return redirect(url_for('clients'))
        client = db_exec('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ? AND owner_id = ?', (client_id, session['user_id']), 'one')
        return render_template('edit_client.html', client=client, error=error)
    client = db_exec('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ? AND owner_id = ?', (client_id, session['user_id']), 'one')
    return render_template('edit_client.html', client=client, error="Client not found." if not client else None)

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    # Get client name before deletion for cleanup
    client = db_exec('SELECT client_name FROM clients WHERE id = ? AND owner_id = ?', (client_id, session['user_id']), 'one')
    if client:
        client_name = client[0]
        # Delete the client
        db_exec('DELETE FROM clients WHERE id = ? AND owner_id = ?', (client_id, session['user_id']))
        # Clean up any references to this client in other tables (if they exist)
        try:
            # Example: Clean up invoices that reference this client
            db_exec('DELETE FROM invoices WHERE client_name = ? AND owner_id = ?', (client_name, session['user_id']))
        except:
            pass  # Invoices table might not exist yet
        # Reset client IDs to start from 1 and fill gaps
        reset_clients_ids()
        flash(f'Client "{client_name}" deleted successfully.')
    else:
        flash('Client not found or access denied.')
    return redirect(url_for('clients'))

@app.route('/payments')
def payments():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('payments'): return render_template('access_restricted.html')
    # Get data based on user permissions for clients
    clients_where_clause, clients_params = get_data_filter_for_module('clients')
    if clients_where_clause:
        clients_data = db_exec(f'SELECT * FROM clients {clients_where_clause} ORDER BY client_name', clients_params, 'all') or []
    else:
        clients_data = db_exec('SELECT * FROM clients ORDER BY client_name', (), 'all') or []
    # Convert to objects for easier template access
    clients = []
    for client in clients_data:
        clients.append({
            'id': client[0],
            'client_name': client[1],
            'email': client[2],
            'phone': client[3],
            'account_type': client[4],
            'company_name': client[5],
            'actions': client[6],
            'created_date': client[7]
        })
    
    # Get invoices based on user permissions for payments
    invoices_where_clause, invoices_params = get_data_filter_for_module('payments')
    if invoices_where_clause:
        invoices_data = db_exec(f'SELECT * FROM invoices {invoices_where_clause} ORDER BY created_date DESC', invoices_params, 'all') or []
    else:
        invoices_data = db_exec('SELECT * FROM invoices ORDER BY created_date DESC', (), 'all') or []
    
    return render_template('payments.html', clients=clients, invoices=invoices_data)

@app.route('/calendar')
def calendar():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('calendar'): return render_template('access_restricted.html')
    
    from calendar import monthrange
    
    actual_today = datetime.now().date()
    current_year, current_month, current_day = request.args.get('year', actual_today.year, type=int), request.args.get('month', actual_today.month, type=int), request.args.get('day', actual_today.day, type=int)
    view, current_date = request.args.get('view', 'month'), datetime(current_year, current_month, current_day)
    
    # Get all tasks owned by the user (not filtered by assigned user)
    tasks = get_all_tasks()
    
    # Build tasks by date dictionary
    tasks_by_date = {}
    for task in tasks:
        if task[3]:  # task_date
            task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
            if task_date not in tasks_by_date:
                tasks_by_date[task_date] = []
            tasks_by_date[task_date].append(task)
    
    # Generate calendar data
    calendar_data = []
    
    if view == 'month':
        # Get first day of month and number of days
        first_day = datetime(current_year, current_month, 1)
        days_in_month = monthrange(current_year, current_month)[1]
        start_weekday = first_day.weekday()  # Monday = 0, Sunday = 6
        
        # Adjust for Sunday = 0 calendar layout
        start_weekday = (start_weekday + 1) % 7
        
        # Add empty cells for days before month starts
        for _ in range(start_weekday):
            calendar_data.append({'day': None, 'tasks': [], 'is_today': False})
        
        # Add actual days of the month
        for day in range(1, days_in_month + 1):
            current_day_date = datetime(current_year, current_month, day).date()
            day_tasks = tasks_by_date.get(current_day_date, [])
            is_today = current_day_date == actual_today
            
            calendar_data.append({
                'day': day,
                'tasks': day_tasks,
                'is_today': is_today,
                'date': current_day_date
            })
    
    elif view == 'week':
        # Calculate week start (Sunday)
        current_date_obj = datetime(current_year, current_month, current_day).date()
        days_since_sunday = (current_date_obj.weekday() + 1) % 7
        week_start = current_date_obj - timedelta(days=days_since_sunday)
        
        # Generate 7 days for the week
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_tasks = tasks_by_date.get(day_date, [])
            is_today = day_date == actual_today
            
            calendar_data.append({
                'day': day_date.day,
                'tasks': day_tasks,
                'is_today': is_today,
                'date': day_date
            })
    
    # Generate header text
    if view == 'month':
        header_text = f"{datetime(current_year, current_month, 1).strftime('%B %Y')}"
    elif view == 'week':
        week_start_date = calendar_data[0]['date'] if calendar_data else current_date.date()
        week_end_date = calendar_data[6]['date'] if len(calendar_data) > 6 else current_date.date()
        header_text = f"Week of {week_start_date.strftime('%B %d')} - {week_end_date.strftime('%B %d, %Y')}"
    else:
        header_text = f"{current_date.strftime('%B %d, %Y')}"
    
    # Get all users for task assignment
    users_data = db_exec('SELECT id, name, email, role FROM users ORDER BY role DESC, name', fetch='all') or []
    users = [{'id': user[0], 'name': user[1], 'email': user[2], 'role': user[3]} for user in users_data]
    
    return render_template('calendar.html', 
                         tasks=tasks, 
                         calendar_data=calendar_data,
                         header_text=header_text,
                         current_year=current_year, 
                         current_month=current_month, 
                         current_day=current_day, 
                         view=view, 
                         today=actual_today, 
                         users=users)

@app.route('/products')
def products():
    if not has_permission('products'): return render_template('access_restricted.html')
    return render_template('products.html')

@app.route('/products_list', methods=['GET', 'POST'])
def products_list():
    if not has_permission('products') and not has_permission('products_list'): return render_template('access_restricted.html')
    if request.method == 'POST':
        try:
            flash('Product data updated successfully')
            return redirect(url_for('products_list'))
        except Exception as e: flash(f'Error processing product data: {str(e)}')
    product_data = {'bamboo_24m_stock': 10, 'bamboo_24m_price': 25.00, 'bamboo_2m_stock': 15, 'bamboo_2m_price': 20.00, 'bamboo_18m_stock': 12, 'bamboo_18m_price': 18.00, 'pebbles_black_stock': 50, 'pebbles_black_price': 5.00, 'pebbles_white_stock': 45, 'pebbles_white_price': 5.50, 'fountain_stock': 3, 'fountain_price': 'Custom Quote', 'premium_stock': 20, 'premium_price': 35.00, 'green_lush_stock': 25, 'green_lush_price': 30.00, 'natural_40mm_stock': 18, 'natural_40mm_price': 32.00, 'golf_turf_stock': 22, 'golf_turf_price': 40.00, 'imperial_lush_stock': 16, 'imperial_lush_price': 38.00, 'pegs_stock': 100, 'pegs_price': 2.50, 'artificial_hedges_stock': 30, 'artificial_hedges_price': 15.00, 'adhesive_tape_stock': 25, 'adhesive_tape_price': 8.00}
    return render_template('products_list.html', **product_data)

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    if request.method == 'POST':
        try:
            name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
            if not all([name, email, password]): flash('All fields are required')
            elif db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one'): flash('Email already exists')
            else:
                hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                user_role = 'admin' if request.form.get('role') == 'admin' else 'user'
                permissions = 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles' if user_role == 'admin' else 'dashboard'
                db_exec('INSERT INTO users (name, email, password_hash, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, hash_pw, user_role, permissions))
                reorganize_user_ids()
                flash('User created successfully')
                return redirect(url_for('profiles'))
        except Exception as e: flash(f'Error creating user: {str(e)}')
    users = db_exec('SELECT id, name, email, role FROM users ORDER BY id', fetch='all') or []
    return render_template('profiles.html', users=users)

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    current_user = db_exec('SELECT role FROM users WHERE id = ?', (user_id,), 'one')
    if current_user:
        new_role = 'user' if current_user[0] == 'admin' else 'admin'
        new_permissions = 'dashboard,payments,clients,calendar,products,profiles' if new_role == 'admin' else 'dashboard'
        db_exec('UPDATE users SET role = ?, permissions = ? WHERE id = ?', (new_role, new_permissions, user_id))
        ensure_admin_exists()
    return redirect(url_for('profiles'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    if user_id == session['user_id']: ensure_admin_exists()
    db_exec('DELETE FROM users WHERE id = ?', (user_id,))
    reorganize_user_ids()
    if user_id == session['user_id']: return redirect(url_for('logout'))
    return redirect(url_for('profiles'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    user = db_exec('SELECT id, name, email, role FROM users WHERE id = ?', (user_id,), 'one')
    if not user: flash('User not found'); return redirect(url_for('profiles'))
    if request.method == 'POST':
        try:
            name, email = request.form.get('name'), request.form.get('email')
            if not all([name, email]): flash('Name and email are required')
            else:
                existing = db_exec('SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id), 'one')
                if existing: flash('Email already exists')
                else:
                    user_role = 'admin' if request.form.get('role') == 'admin' else 'user'
                    db_exec('UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?', (name, email, user_role, user_id))
                    ensure_admin_exists()
                    flash('User updated successfully - use Permissions button to manage access')
                    return redirect(url_for('profiles'))
        except Exception as e: flash(f'Error updating user: {str(e)}')
    return render_template('edit_user.html', user=user)

@app.route('/manage_permissions/<int:user_id>', methods=['GET', 'POST'])
def manage_permissions(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    user = db_exec('SELECT id, name, email, role, permissions FROM users WHERE id = ?', (user_id,), 'one')
    if not user: flash('User not found'); return redirect(url_for('profiles'))
    
    if request.method == 'POST':
        try:
            # Get all available permissions
            available_permissions = ['dashboard', 'payments', 'clients', 'calendar', 'products', 'products_list', 'invoice', 'quotes', 'profiles']
            selected_permissions = []
            
            # Check which permissions were selected
            for permission in available_permissions:
                if request.form.get(f'permission_{permission}'):
                    selected_permissions.append(permission)
            
            # Ensure at least dashboard permission
            if 'dashboard' not in selected_permissions:
                selected_permissions.append('dashboard')
            
            # Save permissions to database
            permissions_string = ','.join(selected_permissions)
            db_exec('UPDATE users SET permissions = ? WHERE id = ?', (permissions_string, user_id))
            
            flash(f'Permissions updated successfully for {user[1]}')
            return redirect(url_for('profiles'))
        except Exception as e: 
            flash(f'Error updating permissions: {str(e)}')
    
    # Parse current permissions
    current_permissions = (user[4] or '').split(',') if user[4] else []
    return render_template('manage_permissions.html', user=user, current_permissions=current_permissions)

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        new_password = request.form.get('new_password', '').strip()
        
        if not email or not new_password:
            flash('Please enter both email and new password.')
            return render_template('forgotpassword.html')
        
        user = db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one')
        if user:
            # Hash the new password and update the user
            new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            db_exec('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, email))
            flash('Password updated successfully! You can now login with your new password.')
            return redirect(url_for('login'))
        else:
            flash('Email address not found.')
    return render_template('forgotpassword.html')

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('quotes'): return render_template('access_restricted.html')
    if request.method == 'POST':
        # Process quote form data
        client_name = request.form.get('client_name', '').strip()
        turf_type = request.form.get('turf_type', '')
        area_str = request.form.get('area_in_sqm', '0')
        area = float(area_str) if area_str else 0
        other_products = request.form.get('other_products', '')
        # Calculate total price (simplified calculation)
        turf_prices = {'Golden Imperial Lush': 15, 'Golden Green Lush': 19, 'Golden Natural 40mm': 17, 'Golden Golf Turf': 22, 'Golden Premium Turf': 20}
        turf_price = turf_prices.get(turf_type, 0)
        total_price = area * turf_price
        summary = {'client_name': client_name, 'turf_type': turf_type, 'area_in_sqm': area, 'other_products': other_products, 'total_price': total_price}
        flash('Quote generated successfully!')
        return render_template('quotes.html', summary=summary)
    return render_template('quotes.html')

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('invoice'): return render_template('access_restricted.html')
    
    if request.method == 'POST':
        print("DEBUG: Invoice form submitted")  # Debug line
        print(f"DEBUG: Form data: {dict(request.form)}")  # Debug line
        try:
            # Get form data
            client_name = request.form.get('client_name', '').strip()
            turf_type = request.form.get('turf_type', '').strip()
            area_str = request.form.get('area', '0').strip()
            area = float(area_str) if area_str and area_str != '' else 0
            payment_status = request.form.get('payment_status', '').strip()
            gst_checkbox = request.form.get('gst')
            
            print(f"DEBUG: Parsed - client_name: {client_name}, turf_type: {turf_type}, area: {area}, payment_status: {payment_status}")
            
            # Extras data - handle empty strings better
            try:
                artificial_hedges_qty = int(request.form.get('artificial_hedges_qty', '0') or '0')
            except ValueError:
                artificial_hedges_qty = 0
            
            try:
                fountain_price = float(request.form.get('fountain_price', '0') or '0')
            except ValueError:
                fountain_price = 0
                
            bamboo_products_size = request.form.get('bamboo_products_size', 'none')
            
            try:
                bamboo_products_qty = int(request.form.get('bamboo_products_qty', '0') or '0')
            except ValueError:
                bamboo_products_qty = 0
                
            pebbles_custom_type = request.form.get('pebbles_custom_type', '')
            
            try:
                pebbles_qty = int(request.form.get('pebbles_qty', '0') or '0')
            except ValueError:
                pebbles_qty = 0
                
            try:
                pegs_qty = int(request.form.get('pegs_qty', '0') or '0')
            except ValueError:
                pegs_qty = 0
                
            try:
                adhesive_tape_qty = int(request.form.get('adhesive_tape_qty', '0') or '0')
            except ValueError:
                adhesive_tape_qty = 0
            
            # Basic validation - make client_name the only required field
            if not client_name:
                flash('Client name is required')
                raise ValueError('Client name required')
            
            # Make payment status default to Unpaid if not provided
            if not payment_status:
                payment_status = 'Unpaid'
            
            # Calculate pricing
            turf_prices = {
                'Golden Imperial Lush': 38.00,
                'Golden Green Lush': 30.00,
                'Golden Natural 40mm': 32.00,
                'Golden Golf Turf': 40.00,
                'Golden Premium Turf': 35.00
            }
            
            # Calculate subtotal
            subtotal = 0
            if turf_type != 'none' and area > 0:
                turf_price = turf_prices.get(turf_type, 0)
                subtotal += turf_price * area
            
            # Add extras
            if artificial_hedges_qty > 0:
                subtotal += artificial_hedges_qty * 15.00
            if fountain_price > 0:
                subtotal += fountain_price
            if bamboo_products_qty > 0:
                bamboo_prices = {'2m': 20.00, '2.4m': 25.00, '1.8m': 18.00}
                bamboo_price = bamboo_prices.get(bamboo_products_size, 0)
                subtotal += bamboo_products_qty * bamboo_price
            if pebbles_qty > 0:
                subtotal += pebbles_qty * 5.50  # Average pebble price
            if pegs_qty > 0:
                subtotal += pegs_qty * 2.50
            if adhesive_tape_qty > 0:
                subtotal += adhesive_tape_qty * 8.00
            
            # Calculate GST and total
            gst_amount = subtotal * 0.10 if gst_checkbox == 'yes' else 0
            total = subtotal + gst_amount
            
            # Create extras description
            extras_list = []
            if artificial_hedges_qty > 0:
                extras_list.append(f"Artificial Hedges x{artificial_hedges_qty}")
            if fountain_price > 0:
                extras_list.append(f"Fountain (${fountain_price})")
            if bamboo_products_qty > 0:
                extras_list.append(f"Bamboo {bamboo_products_size} x{bamboo_products_qty}")
            if pebbles_qty > 0:
                extras_list.append(f"Pebbles ({pebbles_custom_type}) x{pebbles_qty}")
            if pegs_qty > 0:
                extras_list.append(f"Pegs x{pegs_qty}")
            if adhesive_tape_qty > 0:
                extras_list.append(f"Adhesive Tape x{adhesive_tape_qty}")
            
            extras_text = ', '.join(extras_list) if extras_list else ''
            
            # Calculate due date (30 days from now)
            from datetime import datetime, timedelta
            due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Save invoice
            db_exec('''INSERT INTO invoices 
                      (client_name, turf_type, area, payment_status, gst, subtotal, total, extras, 
                       created_date, due_date, owner_id, artificial_hedges_qty, fountain_price, 
                       bamboo_products_size, bamboo_products_qty, pebbles_custom_type, pebbles_qty, 
                       pegs_qty, adhesive_tape_qty)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (client_name, turf_type, area, payment_status, gst_amount, subtotal, total, 
                     extras_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), due_date, 
                     session['user_id'], artificial_hedges_qty, fountain_price, bamboo_products_size,
                     bamboo_products_qty, pebbles_custom_type, pebbles_qty, pegs_qty, adhesive_tape_qty))
            
            flash(f'Invoice created successfully for {client_name}! Total: ${total:.2f}')
            return redirect(url_for('invoice'))
            
        except Exception as e:
            flash(f'Error creating invoice: {str(e)}')
    
    # Get clients for dropdown autocomplete
    clients_data = db_exec('SELECT client_name FROM clients WHERE owner_id = ? ORDER BY client_name', (session['user_id'],), 'all') or []
    clients = [client[0] for client in clients_data]
    
    # Get invoices for display
    invoices_data = db_exec('SELECT * FROM invoices WHERE owner_id = ? ORDER BY id DESC', (session['user_id'],), 'all') or []
    
    return render_template('invoice.html', clients=clients, invoices=invoices_data)

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks_api():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    tasks = get_all_tasks()
    return jsonify([{'id': t[0], 'title': t[1], 'description': t[2], 'date': t[3], 'time': t[4], 'end_time': t[5], 'location': t[6], 'status': t[7], 'created_at': t[8], 'assigned_user_id': t[9] if len(t) > 9 else None} for t in tasks])

@app.route('/api/tasks', methods=['POST'], endpoint='add_task_api')
def add_task():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    try:
        data = request.get_json()
        print(f"DEBUG: Task creation data: {data}")  # Debug line
        
        # Validate required fields
        if not data.get('title'):
            raise ValueError('Title is required')
        if not data.get('date'):
            raise ValueError('Date is required')
        
        # Use correct column names and include owner_id
        db_exec('INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                (data.get('title'), 
                 data.get('description'), 
                 data.get('date'), 
                 data.get('time'), 
                 data.get('end_time'), 
                 data.get('location'), 
                 data.get('status', 'Not completed'), 
                 data.get('assigned_user_id'), 
                 session['user_id']))
        
        return jsonify({'success': True, 'message': 'Task created successfully'})
    except Exception as e: 
        print(f"DEBUG: Task creation error: {str(e)}")  # Debug line
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    task = db_exec('SELECT * FROM tasks WHERE id = ? AND owner_id = ?', (task_id, session['user_id']), 'one')
    if not task: return jsonify({'error': 'Task not found'}), 404
    return jsonify({'id': task[0], 'title': task[1], 'description': task[2], 'date': task[3], 'time': task[4], 'end_time': task[8], 'location': task[5], 'status': task[6], 'created_at': task[7], 'assigned_user_id': task[10] if len(task) > 10 else None})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    try:
        db_exec('UPDATE tasks SET title=?, description=?, task_date=?, task_time=?, task_end_time=?, location=?, status=?, assigned_user_id=? WHERE id=? AND owner_id=?', (data.get('title'), data.get('description'), data.get('date'), data.get('time'), data.get('end_time'), data.get('location'), data.get('status'), data.get('assigned_user_id'), task_id, session['user_id']))
        return jsonify({'success': True, 'message': 'Task updated successfully'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    try:
        db_exec('DELETE FROM tasks WHERE id = ? AND owner_id = ?', (task_id, session['user_id']))
        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/admin-users', methods=['GET'])
def get_admin_users():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    if not has_permission('profiles'): return jsonify({'error': 'Access denied'}), 403
    admins = db_exec('SELECT id, name, email, role FROM users WHERE role = "admin" ORDER BY id', fetch='all') or []
    admin_list = []
    for admin in admins:
        admin_list.append({
            'id': admin[0],
            'name': admin[1],
            'email': admin[2],
            'role': admin[3],
            'is_current_user': admin[0] == session['user_id']
        })
    return jsonify({'admins': admin_list})

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get the invoice data
    invoice = db_exec('SELECT * FROM invoices WHERE id = ? AND owner_id = ?', (invoice_id, session['user_id']), fetch='one')
    if not invoice:
        flash('Invoice not found or access denied.')
        return redirect(url_for('payments'))
    
    if request.method == 'POST':
        try:
            # Get form data
            client_name = request.form.get('client_name', '').strip()
            payment_status = request.form.get('payment_status', 'Unpaid')
            
            if not client_name:
                flash('Client name is required.')
                return redirect(url_for('edit_invoice', invoice_id=invoice_id))
            
            # Update the invoice
            db_exec('UPDATE invoices SET client_name = ?, payment_status = ? WHERE id = ? AND owner_id = ?', 
                   (client_name, payment_status, invoice_id, session['user_id']))
            
            flash('Invoice updated successfully.')
            return redirect(url_for('payments'))
            
        except Exception as e:
            flash(f'Error updating invoice: {str(e)}')
    
    # Get clients for dropdown
    clients_data = db_exec('SELECT client_name FROM clients WHERE owner_id = ? ORDER BY client_name', (session['user_id'],), 'all') or []
    clients = [client[0] for client in clients_data]
    
    # Price table for the template
    price_table = {
        'Golden Imperial Lush': 15.00,
        'Golden Green Lush': 19.00,
        'Golden Natural 40mm': 17.00,
        'Golden Golf Turf': 22.00,
        'Golden Premium Turf': 20.00
    }
    
    return render_template('edit_invoice.html', invoice=invoice, clients=clients, price_table=price_table)

@app.route('/delete_invoice/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Verify the invoice belongs to the current user
        invoice = db_exec('SELECT id FROM invoices WHERE id = ? AND owner_id = ?', (invoice_id, session['user_id']), fetch='one')
        if not invoice:
            flash('Invoice not found or access denied.')
            return redirect(url_for('payments'))
        
        # Delete the invoice
        db_exec('DELETE FROM invoices WHERE id = ? AND owner_id = ?', (invoice_id, session['user_id']))
        # Reset invoice IDs to start from 1 and fill gaps
        reset_invoices_ids()
        flash('Invoice deleted successfully.')
    except Exception as e:
        flash(f'Error deleting invoice: {str(e)}')
    
    return redirect(url_for('payments'))

if __name__ == '__main__': app.run(debug=True, host='0.0.0.0', port=5000)