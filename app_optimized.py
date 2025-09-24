from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, bcrypt, os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

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

def has_permission(module):
    if 'user_id' not in session: return False
    user = db_exec('SELECT permissions FROM users WHERE id = ?', (session['user_id'],), 'one')
    return user and module in (user[0] or '').split(',')

def migrate_users_table():
    try: db_exec('ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT "dashboard"')
    except: pass
    first = db_exec('SELECT id FROM users ORDER BY id LIMIT 1', fetch='one')
    if first: db_exec("UPDATE users SET role = ?, permissions = ? WHERE id = ?", ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first[0]))

def ensure_admin_exists():
    if not db_exec('SELECT id FROM users WHERE role = "admin"', fetch='one'):
        first_user = db_exec('SELECT id FROM users ORDER BY id LIMIT 1', fetch='one')
        if first_user: db_exec('UPDATE users SET role = ?, permissions = ? WHERE id = ?', ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first_user[0]))
        reorganize_user_ids()

def authenticate_user(email, password):
    user = db_exec('SELECT id, name, password_hash, permissions, role FROM users WHERE email = ?', (email,), 'one')
    if not user: return None
    if user[2] and bcrypt.checkpw(password.encode('utf-8'), user[2]):
        return user
    elif user[2] is None and password == 'Password123':
        new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db_exec('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, user[0]))
        return user
    return None

def create_tasks_table():
    try: db_exec('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, task_date DATE, task_time TIME, end_time TIME, location TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, assigned_user_id INTEGER)''')
    except: pass

def migrate_tasks_table():
    try: db_exec('ALTER TABLE tasks ADD COLUMN assigned_user_id INTEGER')
    except: pass

def get_all_tasks(user_id=None):
    query = 'SELECT * FROM tasks' + (' WHERE assigned_user_id = ?' if user_id else '') + ' ORDER BY task_date, task_time'
    params = (user_id,) if user_id else ()
    return db_exec(query, params, 'all') or []

# Initialize database
migrate_users_table()
ensure_admin_exists()
create_tasks_table()
migrate_tasks_table()

# Routes
@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email', '').strip(), request.form.get('password', '').strip()
        user = authenticate_user(email, password)
        if user:
            session.update({'user_id': user[0], 'user_name': user[1], 'user_email': email})
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, password = request.form.get('name', '').strip(), request.form.get('email', '').strip(), request.form.get('password', '').strip()
        if db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one'):
            flash('Email already registered')
        else:
            hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            db_exec('INSERT INTO users (name, email, password_hash, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, hash_pw, 'user', 'dashboard'))
            flash('Registration successful')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    total_clients = db_exec('SELECT COUNT(*) FROM users WHERE role = "user"', fetch='one')[0] if db_exec('SELECT COUNT(*) FROM users WHERE role = "user"', fetch='one') else 0
    admins = db_exec('SELECT id, name, email FROM users WHERE role = "admin" ORDER BY id', fetch='all') or []
    return render_template('dashboard.html', total_clients=total_clients, admins=admins)

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
                db_exec('INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (contact_name, email, phone_number, account_type, company_name, actions, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session['user_id']))
                success = 'Client saved successfully.'
            except Exception as e: error = f'Failed to save client: {str(e)}'
    client_list = db_exec('SELECT * FROM clients WHERE owner_id = ? ORDER BY id DESC', (session['user_id'],), 'all') or []
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
    db_exec('DELETE FROM clients WHERE id = ? AND owner_id = ?', (client_id, session['user_id']))
    return redirect(url_for('clients'))

@app.route('/payments')
def payments():
    if not has_permission('payments'): return render_template('access_restricted.html')
    return render_template('payments.html')

@app.route('/calendar')
def calendar():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('calendar'): return render_template('access_restricted.html')
    actual_today = datetime.now().date()
    current_year, current_month, current_day = request.args.get('year', actual_today.year, type=int), request.args.get('month', actual_today.month, type=int), request.args.get('day', actual_today.day, type=int)
    view, current_date = request.args.get('view', 'month'), datetime(current_year, current_month, current_day)
    tasks = get_all_tasks(session['user_id'])
    task_dates = {}
    for task in tasks:
        if task[3]:
            task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
            if task_date not in task_dates: task_dates[task_date] = []
            task_dates[task_date].append({'id': task[0], 'title': task[1], 'time': task[4] or '', 'status': task[7] or 'pending'})
    tasks_by_date = {}
    full_day_tasks = []
    if view == 'month':
        for task in tasks:
            if task[3]:
                task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
                if task_date.year == current_year and task_date.month == current_month:
                    if task_date not in tasks_by_date: tasks_by_date[task_date] = []
                    tasks_by_date[task_date].append({'id': task[0], 'title': task[1], 'time': task[4] or '', 'status': task[7] or 'pending'})
    elif view == 'day':
        for task in tasks:
            if task[3]:
                task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
                if task_date == current_date.date():
                    if task[4]: full_day_tasks.append({'id': task[0], 'title': task[1], 'time': task[4], 'status': task[7] or 'pending'})
                    else: full_day_tasks.append({'id': task[0], 'title': task[1], 'time': 'All day', 'status': task[7] or 'pending'})
    return render_template('calendar.html', tasks=tasks, task_dates=task_dates, tasks_by_date=tasks_by_date, current_year=current_year, current_month=current_month, current_day=current_day, view=view, today=actual_today, full_day_tasks=full_day_tasks, current_date=current_date.strftime('%Y-%m-%d') if view == 'day' else None, users=[])

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
                    permissions = 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles' if user_role == 'admin' else 'dashboard'
                    db_exec('UPDATE users SET name = ?, email = ?, role = ?, permissions = ? WHERE id = ?', (name, email, user_role, permissions, user_id))
                    ensure_admin_exists()
                    flash('User updated successfully')
                    return redirect(url_for('profiles'))
        except Exception as e: flash(f'Error updating user: {str(e)}')
    return render_template('edit_user.html', user=user)

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if db_exec('SELECT id FROM users WHERE email = ?', (email,), 'one'):
            flash('If this email exists, you will receive password reset instructions.')
        else: flash('If this email exists, you will receive password reset instructions.')
    return render_template('forgotpassword.html')

@app.route('/quotes')
def quotes():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('quotes'): return render_template('access_restricted.html')
    return render_template('quotes.html')

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('invoice'): return render_template('access_restricted.html')
    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        if client_name:
            try:
                flash('Invoice created successfully')
                return redirect(url_for('invoice'))
            except Exception as e: flash(f'Error creating invoice: {str(e)}')
    return render_template('invoice.html')

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
        db_exec('INSERT INTO tasks (title, description, task_date, task_time, end_time, location, status, assigned_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (data.get('title'), data.get('description'), data.get('date'), data.get('time'), data.get('end_time'), data.get('location'), data.get('status', 'pending'), data.get('assigned_user_id')))
        return jsonify({'success': True, 'message': 'Task created successfully'})
    except Exception as e: return jsonify({'error': str(e)}), 500

if __name__ == '__main__': app.run(debug=True, host='0.0.0.0', port=5000)