"""Golden Turf Business Management System"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import sqlite3, secrets, bcrypt
from calendar import monthcalendar

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(hours=1)

def reorganize_user_ids():
    """Reorganize user IDs to be successive after deletions"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Get all users ordered by current ID
        c.execute('SELECT id, name, email, password, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        
        if len(users) <= 1:
            conn.close()
            return  # No need to reorganize if 0 or 1 users
        
        # Check if IDs are already successive
        expected_ids = list(range(1, len(users) + 1))
        current_ids = [user[0] for user in users]
        
        if current_ids == expected_ids:
            conn.close()
            return  # Already successive, no need to reorganize
        
        # Clear table and reinsert with successive IDs
        c.execute('DELETE FROM users')
        for i, user in enumerate(users, start=1):
            c.execute('INSERT INTO users (id, name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?, ?)',
                     (i, user[1], user[2], user[3], user[4], user[5]))
        
        conn.commit()
        conn.close()
        print(f"✅ Reorganized user IDs: {current_ids} → {expected_ids}")
    except Exception as e:
        print(f"Error reorganizing user IDs: {e}")

def has_permission(module):
    if session.get('user_role') == 'admin': return True
    perms = session.get('user_permissions', '').split(',') if session.get('user_permissions') else []
    return module in perms or (module == 'products_list' and 'products' in perms) or (module == 'products' and 'products_list' in perms)

def migrate_users_table():
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("PRAGMA table_info(users)"); cols = [col[1] for col in c.fetchall()]
        for col, query in [('reset_token','ALTER TABLE users ADD COLUMN reset_token TEXT'),('token_expiry','ALTER TABLE users ADD COLUMN token_expiry TEXT'),('role','ALTER TABLE users ADD COLUMN role TEXT DEFAULT "user"'),('verification_code','ALTER TABLE users ADD COLUMN verification_code TEXT'),('permissions','ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ""')]:
            if col not in cols: c.execute(query)
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        if c.fetchone()[0] == 0:
            c.execute("SELECT id FROM users ORDER BY id LIMIT 1"); first = c.fetchone()
            if first: c.execute("UPDATE users SET role = ?, permissions = ? WHERE id = ?", ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first[0]))
        conn.commit(); conn.close()
    except: pass

def ensure_admin_exists():
    """Ensure at least one admin user exists in the system"""
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        
        if admin_count == 0:
            # Find the user with the lowest ID and make them admin
            c.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            first_user = c.fetchone()
            if first_user:
                c.execute("UPDATE users SET role = ?, permissions = ? WHERE id = ?", 
                         ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles', first_user[0]))
                conn.commit()
                print(f"✅ User with ID {first_user[0]} promoted to admin (no admin existed)")
        conn.close()
    except Exception as e:
        print(f"Error ensuring admin exists: {e}")

def authenticate_user(email, password):
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute('SELECT id, name, role, password, permissions FROM users WHERE email = ?', (email,)); user = c.fetchone(); conn.close()
        if user:
            stored_password = user[3]
            # Ensure stored_password is a string
            if isinstance(stored_password, bytes):
                stored_password = stored_password.decode('utf-8')
            
            # Handle bcrypt hashed passwords
            if stored_password.startswith('$2b$'):
                if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                    return user
            # Handle plain text passwords (for manually added users)
            elif stored_password == password:
                # Convert plain text password to bcrypt hash for security
                try:
                    conn = sqlite3.connect('users.db'); c = conn.cursor()
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user[0]))
                    conn.commit(); conn.close()
                    print(f"✅ Converted plain text password to bcrypt for user {user[1]} ({email})")
                except Exception as e:
                    print(f"Warning: Could not update password hash for user {user[0]}: {e}")
                return user
    except Exception as e:
        print(f"Authentication error: {e}")
    return None

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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        assigned_user_id INTEGER,
        owner_id INTEGER
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
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER")
        conn.commit()
    conn.close()

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

@app.route('/')
def home(): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form.get('email'), request.form.get('password')
        if not email or not password: flash('Email and password required'); return render_template('login.html')
        user_data = authenticate_user(email, password)
        if user_data: 
            session.update({'user_id': user_data[0], 'user_name': user_data[1], 'user_email': email, 'user_role': user_data[2], 'user_permissions': user_data[4]}); return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, password = request.form.get('name'), request.form.get('email'), request.form.get('password')
        if not all([name, email, password]): flash('All fields required'); return render_template('register.html')
        try:
            conn = sqlite3.connect('users.db'); c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            if c.fetchone(): flash('Email already exists'); return render_template('register.html')
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, hashed_password, 'user', ''))
            conn.commit(); conn.close(); flash('Registration successful'); return redirect(url_for('login'))
        except Exception: flash('Registration failed')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    # Add total_clients calculation and admin users
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users WHERE role = "user"')  # Assuming clients are users with role 'user'
        total_clients = c.fetchone()[0]
        # Fetch admin users for display (include ID for template comparison)
        c.execute('SELECT name, email, id FROM users WHERE role = "admin"')
        admins = c.fetchall()
        conn.close()
    except Exception:
        total_clients = 0
        admins = []
    return render_template('dashboard.html', total_clients=total_clients, admins=admins)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    
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
        owner_id = session.get('user_id')
        
        # Basic validation
        if not contact_name:
            error = 'Contact name is required.'
        elif not account_type or account_type not in ['Active', 'Deactivated']:
            error = 'Please select a valid account type.'
        elif not email or '@' not in email or '.' not in email:
            error = 'Please enter a valid email address.'
        
        if not error:
            try:
                c.execute('''INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                             (contact_name, email, phone_number, account_type, company_name, actions, created_date, owner_id))
                conn.commit()
                success = 'Client saved successfully.'
            except Exception as e:
                error = f'Failed to save client: {str(e)}'
    
    # Get clients for the current user
    c.execute('SELECT * FROM clients WHERE owner_id = ? ORDER BY id DESC', (session.get('user_id'),))
    client_list = c.fetchall()
    conn.close()
    
    return render_template('clients.html', clients=client_list, error=error, success=success)

@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        account_type = request.form.get('account_type', '')
        company_name = request.form.get('company_name', '')
        email = request.form.get('email', '')
        actions = request.form.get('actions', '').strip()
        owner_id = session.get('user_id')
        
        # Basic validation
        error = None
        if not contact_name:
            error = 'Contact name is required.'
        elif not account_type or account_type not in ['Active', 'Deactivated']:
            error = 'Please select a valid account type.'
        elif not email or '@' not in email or '.' not in email:
            error = 'Please enter a valid email address.'
        
        if not error:
            # Update client in database
            c.execute('''UPDATE clients SET client_name=?, phone=?, account_type=?, company_name=?, email=?, actions=? WHERE id=? AND owner_id=?''',
                      (contact_name, phone_number, account_type, company_name, email, actions, client_id, owner_id))
            conn.commit()
            conn.close()
            return redirect(url_for('clients'))
        else:
            # Get client data for re-displaying form with error
            c.execute('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ? AND owner_id = ?', (client_id, owner_id))
            client = c.fetchone()
            conn.close()
            return render_template('edit_client.html', client=client, error=error)
    
    # GET request - load client data
    c.execute('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ? AND owner_id = ?', (client_id, session.get('user_id')))
    client = c.fetchone()
    conn.close()
    
    if not client:
        return render_template('edit_client.html', error="Client not found.")
    
    return render_template('edit_client.html', client=client)

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('clients'): return render_template('access_restricted.html')
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Delete client (only if owned by current user)
    c.execute('DELETE FROM clients WHERE id = ? AND owner_id = ?', (client_id, session.get('user_id')))
    conn.commit()
    conn.close()
    
    return redirect(url_for('clients'))

@app.route('/payments')
def payments():
    if not has_permission('payments'): return render_template('access_restricted.html')
    return render_template('payments.html')

@app.route('/calendar')
def calendar():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('calendar'): return render_template('access_restricted.html')

    # Calendar navigation parameters
    actual_today = datetime.now().date()
    current_year, current_month, current_day = request.args.get('year', actual_today.year, type=int), request.args.get('month', actual_today.month, type=int), request.args.get('day', actual_today.day, type=int)
    view, current_date = request.args.get('view', 'month'), datetime(current_year, current_month, current_day)

    # Organize tasks by date with colors
    tasks, tasks_by_date = get_all_tasks(), {}
    status_colors = {'Not completed': 'red', 'In Progress': 'orange', 'Completed': 'green'}
    for task in tasks:
        task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
        task = list(task) + [status_colors.get(task[7], 'gray')]
        tasks_by_date.setdefault(task_date, []).append(task)

    # Calendar data generation
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    calendar_data, full_day_tasks = [], []

    if view == 'month':
        from calendar import Calendar
        cal, today = Calendar(firstweekday=6), current_date.date()
        for day in cal.itermonthdays(current_year, current_month):
            if day == 0: calendar_data.append({'day': None, 'tasks': [], 'is_today': False})
            else: 
                date = datetime(current_year, current_month, day).date()
                calendar_data.append({'day': day, 'tasks': tasks_by_date.get(date, []), 'is_today': date == today})
        header_text = month_names[current_month - 1]
    elif view == 'week':
        weekday = current_date.weekday()
        days_to_sunday = (weekday + 1) % 7
        start_of_week = current_date - timedelta(days=days_to_sunday)
        for i in range(7):
            date = start_of_week + timedelta(days=i)
            calendar_data.append({'day': date.day, 'tasks': tasks_by_date.get(date.date(), []), 'is_today': date.date() == actual_today})
        # Week header with ordinal suffixes
        get_suffix = lambda d: 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')
        end_of_week = start_of_week + timedelta(days=6)
        if start_of_week.month == end_of_week.month and start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{get_suffix(start_of_week.day)} - {end_of_week.day}{get_suffix(end_of_week.day)})"
        else:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{get_suffix(start_of_week.day)}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{get_suffix(end_of_week.day)})"

    # Fetch users for dropdown
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute('SELECT id, name FROM users ORDER BY name'); users = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]; conn.close()
    
    return render_template('calendar.html', calendar_data=calendar_data, current_year=current_year, current_month=current_month, current_day=current_day, header_text=header_text, view=view, tasks=tasks, full_day_tasks=full_day_tasks, users=users)

@app.route('/products')
def products():
    if not has_permission('products'): return render_template('access_restricted.html')
    return render_template('products.html')

@app.route('/products_list', methods=['GET', 'POST'])
def products_list():
    if not has_permission('products') and not has_permission('products_list'): 
        return render_template('access_restricted.html')
    
    if request.method == 'POST':
        try:
            # Handle POST data safely
            form_data = request.form.to_dict()
            # Process form data here if needed
            flash('Product data updated successfully')
            return redirect(url_for('products_list'))
        except Exception as e:
            flash(f'Error processing product data: {str(e)}')
    
    # Complete product data for the template
    product_data = {
        # Bamboo products
        'bamboo_24m_stock': 10, 'bamboo_24m_price': 25.00,
        'bamboo_2m_stock': 15, 'bamboo_2m_price': 20.00, 
        'bamboo_18m_stock': 12, 'bamboo_18m_price': 18.00,
        
        # Pebbles
        'pebbles_black_stock': 50, 'pebbles_black_price': 5.00,
        'pebbles_white_stock': 45, 'pebbles_white_price': 5.50,
        
        # Fountain
        'fountain_stock': 3, 'fountain_price': 'Custom Quote',
        
        # Premium turf varieties
        'premium_stock': 20, 'premium_price': 35.00,
        'green_lush_stock': 25, 'green_lush_price': 30.00,
        'natural_40mm_stock': 18, 'natural_40mm_price': 32.00,
        'golf_turf_stock': 22, 'golf_turf_price': 40.00,
        'imperial_lush_stock': 16, 'imperial_lush_price': 38.00,
        
        # Accessories
        'pegs_stock': 100, 'pegs_price': 2.50,
        'artificial_hedges_stock': 30, 'artificial_hedges_price': 15.00,
        'adhesive_tape_stock': 25, 'adhesive_tape_price': 8.00
    }
    
    return render_template('products_list.html', **product_data)

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    
    if request.method == 'POST':
        try:
            # Handle user creation
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not all([name, email, password]):
                flash('All fields are required')
                return redirect(url_for('profiles'))
            
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            
            # Check if email already exists
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            if c.fetchone():
                flash('Email already exists')
                conn.close()
                return redirect(url_for('profiles'))
            
            # Create new user
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                     (name, email, hashed_password, 'user', 'dashboard'))
            conn.commit()
            conn.close()
            
            flash('User created successfully')
            return redirect(url_for('profiles'))
        except Exception as e:
            flash(f'Error creating user: {str(e)}')
    
    # Get all users for admin management
    try:
        # Ensure user IDs are successive before displaying
        reorganize_user_ids()
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Count total users
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        # If only one user exists and it's ID 1, ensure they're admin
        if total_users == 1:
            c.execute('SELECT id FROM users WHERE id = 1')
            if c.fetchone():
                # Ensure user ID 1 is admin when they're the only user
                c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = 1', 
                         ('admin', 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles'))
                conn.commit()
        
        c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
        users = c.fetchall()
        
        # Check if only one admin exists and get their ID
        c.execute('SELECT id FROM users WHERE role = "admin"')
        admin_users = c.fetchall()
        only_admin_id = admin_users[0][0] if len(admin_users) == 1 else None
        
        conn.close()
        
        return render_template('profiles.html', users=users, only_admin_id=only_admin_id)
    except Exception as e:
        flash(f'Error loading profiles: {str(e)}')
        return render_template('profiles.html', users=[], only_admin_id=None)

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Get current user role
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        current_role = c.fetchone()
        if not current_role: 
            flash('User not found')
            return redirect(url_for('profiles'))
        
        # Check if this is the only admin (prevent removing last admin)
        c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
        admin_count = c.fetchone()[0]
        
        if current_role[0] == 'admin' and admin_count <= 1:
            flash('Cannot remove the last admin user')
            return redirect(url_for('profiles'))
        
        # Toggle role
        new_role = 'user' if current_role[0] == 'admin' else 'admin'
        new_permissions = 'dashboard,payments,clients,calendar,products,profiles' if new_role == 'admin' else 'dashboard'
        
        c.execute('UPDATE users SET role = ?, permissions = ? WHERE id = ?', (new_role, new_permissions, user_id))
        conn.commit()
        conn.close()
        
        flash(f'User role updated to {new_role}')
    except Exception as e:
        flash(f'Error updating user role: {str(e)}')
    
    return redirect(url_for('profiles'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Simple deletion - complex logic handled by frontend
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        # Reorganize user IDs to be successive
        reorganize_user_ids()
        
        # If user deleted themselves, logout
        if user_id == session['user_id']:
            session.clear()
            flash('Your account has been deleted successfully')
            return redirect(url_for('login'))
        else:
            flash('User deleted successfully')
            return redirect(url_for('profiles'))
            
    except Exception as e:
        flash(f'Error deleting user: {str(e)}')
        return redirect(url_for('profiles'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    if not has_permission('profiles'): return render_template('access_restricted.html')
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            
            # Handle permissions
            if role == 'admin':
                permissions = 'dashboard,payments,clients,calendar,products,products_list,invoice,quotes,profiles'
            else:
                # Get selected permissions from checkboxes
                selected_permissions = request.form.getlist('permissions')
                permissions = ','.join(selected_permissions) if selected_permissions else 'dashboard'
            
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            
            # Update user info including role and permissions
            if password:
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                c.execute('UPDATE users SET name = ?, email = ?, password = ?, role = ?, permissions = ? WHERE id = ?', 
                         (name, email, hashed_password, role, permissions, user_id))
            else:
                c.execute('UPDATE users SET name = ?, email = ?, role = ?, permissions = ? WHERE id = ?', 
                         (name, email, role, permissions, user_id))
            
            conn.commit()
            conn.close()
            flash('User updated successfully')
            return redirect(url_for('profiles'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}')
            return redirect(url_for('profiles'))
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            flash('User not found')
            return redirect(url_for('profiles'))
        
        return render_template('edit_user.html', user=user)
    except Exception as e:
        flash(f'Error loading user: {str(e)}')
        return redirect(url_for('profiles'))

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if email: flash('Password reset instructions sent to email')
    return render_template('forgotpassword.html')

@app.route('/quotes')
def quotes():
    print(f"DEBUG: User role: {session.get('user_role')}, Permissions: {session.get('user_permissions')}")
    if not has_permission('quotes'): return render_template('access_restricted.html')
    return render_template('quotes.html')

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    # Allow access for admins or users with invoice permission
    if not has_permission('invoice') and session.get('user_role') != 'admin':
        return render_template('access_restricted.html')
    
    if request.method == 'POST':
        try:
            # Handle invoice form submission
            form_data = request.form.to_dict()
            flash('Invoice processed successfully')
            return redirect(url_for('invoice'))
        except Exception as e:
            flash(f'Error processing invoice: {str(e)}')
    
    return render_template('invoice.html')

# Task management API endpoints
@app.route('/api/tasks', methods=['GET'])
def get_all_tasks_api():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    tasks = get_all_tasks()
    return jsonify([{'id': t[0], 'title': t[1], 'description': t[2], 'date': t[3], 'time': t[4], 'end_time': t[5], 'location': t[6], 'status': t[7], 'created_at': t[8], 'assigned_user_id': t[9] if len(t) > 9 else None} for t in tasks])

@app.route('/api/tasks', methods=['POST'], endpoint='add_task_api')
def add_task_api():
    if 'user_id' not in session:
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
    owner_id = session.get('user_id')

    if not title or not task_date:
        return jsonify({'error': 'Title and date are required'}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id if assigned_user_id else None, owner_id))
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'message': 'Task added successfully', 'task_id': task_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to add task'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)); task = c.fetchone(); conn.close()
    if not task: return jsonify({'error': 'Task not found'}), 404
    return jsonify({'id': task[0], 'title': task[1], 'description': task[2], 'date': task[3], 'time': task[4], 'end_time': task[5], 'location': task[6], 'status': task[7], 'created_at': task[8]})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_id' not in session:
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
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id=?', (task_id,)); conn.commit(); conn.close()
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/api/users')
def api_users():
    if 'user_id' not in session: return jsonify([])
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute('SELECT id, name, role FROM users ORDER BY name'); users = [{'id': row[0], 'name': row[1], 'role': row[2]} for row in c.fetchall()]; conn.close()
    return jsonify(users)

@app.route('/add_task', methods=['POST'], endpoint='add_task_form')
def add_task_form():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not has_permission('calendar'):
        return jsonify({'error': 'Access restricted'}), 403

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

@app.errorhandler(500)
def internal_error(error):
    return f"Internal Server Error: {str(error)}", 500

@app.errorhandler(Exception)
def handle_exception(e):
    return f"Application Error: {str(e)}", 500

if __name__ == '__main__':
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, reset_token TEXT, token_expiry TEXT, role TEXT DEFAULT 'user', verification_code TEXT, permissions TEXT DEFAULT '')""")
        conn.commit(); conn.close(); migrate_users_table(); ensure_admin_exists()
        create_tasks_table(); migrate_tasks_table()
        print("Access your app at: http://127.0.0.1:5000")
    except Exception as e: 
        print(f"Database initialization error: {e}")
    app.run(debug=True, host='127.0.0.1', port=5000)
