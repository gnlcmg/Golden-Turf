from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set a secret key for session management

import json
# ...existing code...
@app.route('/payments-quote', methods=['GET', 'POST'])
def payments_quote():
    error = None
    total_price = None
    price_table = {
        'Golden Imperial Lush': {'Small': 20, 'Medium': 30, 'Large': 40},
        'Golden Green Lush': {'Small': 18, 'Medium': 28, 'Large': 38},
        'Golden Natural 40mm': {'Small': 22, 'Medium': 32, 'Large': 42},
        'Golden Golf Turf': {'Small': 25, 'Medium': 35, 'Large': 45},
        'Golden Premium Turf': {'Small': 28, 'Medium': 38, 'Large': 48}
    }
    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        area_in_sqm = request.form.get('area_in_sqm', type=float)
        turf_type = request.form.get('turf_type')
        size_option = request.form.get('size_option')
        quantity = request.form.get('quantity', type=int)
        if not client_name:
            error = 'Please enter your name'
        elif not area_in_sqm or area_in_sqm <= 0:
            error = 'Area must be more than zero'
        elif not turf_type or turf_type not in price_table:
            error = 'Please select a valid turf type'
        elif not size_option or size_option not in price_table[turf_type]:
            error = 'Please select a valid size option'
        elif not quantity or quantity <= 0:
            error = 'Quantity must be at least 1'
        else:
            price = price_table[turf_type][size_option]
            total_price = round(area_in_sqm * price * quantity, 2)
    return render_template('payments_quote.html', error=error, total_price=total_price)
@app.route('/payments')
def payments():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Fetch invoices with client name and products
    c.execute('''
        SELECT invoices.id, clients.client_name, invoices.status, invoices.due_date, invoices.product, invoices.amount, invoices.gst, invoices.total
        FROM invoices
        LEFT JOIN clients ON invoices.client_id = clients.id
    ''')
    rows = c.fetchall()
    payments = []
    current_date = datetime.now().strftime('%Y-%m-%d')
    for row in rows:
        payments.append({
            'id': row[0],
            'client': row[1],
            'status': row[2],
            'due_date': row[3],
            'products': row[4],
            'amount': row[5],
            'gst': row[6],
            'total': row[7]
        })
    conn.close()
    return render_template('payments.html', payments=payments, current_date=current_date)

## Removed duplicate route definition
from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set a secret key for session management

# Create DB and table if not exists
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # New tables for dashboard
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            phone TEXT,
            created_date TEXT,
            UNIQUE(client_name)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            job_date TEXT,
            status TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            amount REAL,
            payment_date TEXT,
            status TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            product TEXT,
            quantity INTEGER,
            price REAL,
            gst REAL,
            discount REAL,
            total REAL,
            status TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
    ''')
    # Products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE NOT NULL,
            turf_type TEXT NOT NULL,
            description TEXT,
            stock INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                      (name, email, password))
            conn.commit()
            message = 'Registration successful!'
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            message = 'Email already registered!'
        conn.close()
    return render_template('register.html', message=message)

from flask import session

from flask import session

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            message = 'Invalid email or password!'
    return render_template('login.html', message=message)

from flask import session
from datetime import datetime, timedelta

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    # For demo, user_role hardcoded; in real app, get from session or auth
    user_role = 'admin'

    clients = query_all_clients()
    jobs = query_all_jobs()
    payments = query_all_payments()

    today = datetime.datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)

    total_clients = len(clients)
    total_services = sum(1 for job in jobs if job[3] == 'Completed')  # status at index 3

    # Use datetime.strptime from the correct import
    total_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid')  # amount index 3, status index 4
    today_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(str(payment[3]), '%Y-%m-%d').date() == today)
    yesterday_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(str(payment[3]), '%Y-%m-%d').date() == yesterday)
    last_7_days_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(str(payment[3]), '%Y-%m-%d').date() >= last_7_days)

    upcoming_jobs = [job for job in jobs if datetime.strptime(str(job[2]), '%Y-%m-%d').date() >= today]
    overdue_jobs = [job for job in jobs if datetime.strptime(str(job[2]), '%Y-%m-%d').date() < today and job[3] != 'Completed']

    # For each overdue job, get client name
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    overdue_jobs_info = []
    for job in overdue_jobs:
        c.execute('SELECT client_name FROM clients WHERE id = ?', (job[1],))
        client_name = c.fetchone()
        if client_name:
            overdue_jobs_info.append({'client_name': client_name[0], 'job_date': job[2]})
    conn.close()

    return render_template('dashboard.html',
                           total_clients=total_clients,
                           total_services=total_services,
                           total_sales=total_sales,
                           today_sales=today_sales,
                           yesterday_sales=yesterday_sales,
                           last_7_days_sales=last_7_days_sales,
                           overdue_jobs=overdue_jobs_info,
                           user_role=user_role)
    
from datetime import datetime, timedelta

def query_all_clients():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM clients')
    clients = c.fetchall()
    conn.close()
    return clients

def query_all_jobs():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM jobs')
    jobs = c.fetchall()
    conn.close()
    return jobs

def query_all_payments():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM payments')
    payments = c.fetchall()
    conn.close()
    return payments

from flask import session

import sqlite3

def migrate_clients_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(clients)")
    columns = [info[1] for info in c.fetchall()]
    if 'email' not in columns or 'created_date' not in columns:
        c.execute("ALTER TABLE clients RENAME TO clients_old")
        c.execute('''
            CREATE TABLE clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                account_type TEXT,
                company_name TEXT,
                actions TEXT,
                created_date TEXT,
                UNIQUE(client_name)
            )
        ''')
        c.execute('''
            INSERT INTO clients (id, client_name)
            SELECT id, client_name FROM clients_old
        ''')
        c.execute("DROP TABLE clients_old")
        conn.commit()
    conn.close()

migrate_clients_table()

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    if 'user_name' not in session:
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
        created_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Validation
        import re
        if not re.match(r'^[A-Za-z ]+$', contact_name):
            error = 'Contact name is required and must contain only alphabetic characters and spaces.'
        elif phone_number and (not phone_number.isdigit()):
            error = None
        if account_type not in ['Active', 'Deactivated']:
            error = 'Invalid account type selected.'
        elif '@' not in email or '.' not in email:
            error = 'Invalid email format.'

        # Find the lowest available unused ID
        c.execute('SELECT id FROM clients ORDER BY id ASC')
        existing_ids = [row[0] for row in c.fetchall()]
        next_id = 1
        for eid in existing_ids:
            if eid == next_id:
                next_id += 1
            else:
                break

        if not error:
            # Insert with custom id if there's a gap, else let AUTOINCREMENT handle
            if next_id not in existing_ids:
                c.execute('''
                    INSERT INTO clients (id, client_name, email, phone, account_type, company_name, actions, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (next_id, contact_name, email, phone_number, account_type, company_name, actions, created_date))
            else:
                c.execute('''
                    INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (contact_name, email, phone_number, account_type, company_name, actions, created_date))
            conn.commit()
            success = 'Client saved successfully.'

    c.execute('SELECT * FROM clients')
    client_list = c.fetchall()
    conn.close()

    return render_template('clients.html', clients=client_list, error=error, success=success)

@app.route('/logout')
def logout():
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        # Here you would add logic to handle password reset, e.g., send email
        message = 'If this email is registered, a password reset link has been sent.'
    return render_template('forgotpassword.html', message=message)

from flask import session, request

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        client_name = request.form.get('client_name', '')
        turf_type = request.form.get('turf_type', '')
        area = request.form.get('area', '0')
        extra_fee = request.form.get('extra_fee', '0')
        extras = request.form.get('extras', 'none')
        discount = request.form.get('discount', '0')
        payment_status = request.form.get('payment_status', '')
        gst = request.form.get('gst', 'no')
        invoice_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Convert numeric fields safely
        try:
            area_val = float(area)
        except ValueError:
            area_val = 0.0
        try:
            extra_fee_val = float(extra_fee)
        except ValueError:
            extra_fee_val = 0.0
        try:
            discount_percent = float(discount)
        except ValueError:
            discount_percent = 0.0

        discount_val = 0.0  # Always define discount_val

        # Insert invoice into DB
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Find client_id by client_name
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client = c.fetchone()
        client_id = client[0] if client else None

        error = None
        success = None

        if client_id:
            # Calculate total
            extras_costs = {
                'none': 0,
                'artificial_hedges': 50,
                'fountain': 150,
                'bamboo_products': 75,
                'polished_pebbles': 40,
                'pegs': 20
            }
            extra_cost = extras_costs.get(extras, 0)
            subtotal = area_val + extra_fee_val + extra_cost
            discount_val = subtotal * (discount_percent / 100)
            subtotal_after_discount = subtotal - discount_val
            gst_amount = subtotal_after_discount * 0.07 if gst == 'yes' else 0
            total = subtotal_after_discount + gst_amount

            c.execute('''
                INSERT INTO invoices (client_id, product, quantity, price, gst, discount, total, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (client_id, turf_type, area_val, extra_fee_val, gst_amount, discount_val, total, payment_status))
            conn.commit()
            conn.close()
            success = 'Invoice saved successfully.'
        else:
            error = 'Client name not found in database. Please select an existing client.'

        return render_template('invoice.html',
                               client_name=client_name,
                               turf_type=turf_type,
                               area=area_val,
                               extra_fee=extra_fee_val,
                               extras=extras,
                               discount=discount_val,
                               payment_status=payment_status,
                               gst=gst,
                               invoice_id='INV-0001',
                               invoice_date=invoice_date,
                               success=success,
                               error=error)
    else:
        return render_template('invoice.html')

@app.route('/list')
def list_page():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch clients
    c.execute('SELECT id, client_name, phone, created_date, "Active" as status FROM clients')
    clients = c.fetchall()

    # Fetch invoices with client name
    c.execute('''
        SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
               invoices.gst, invoices.discount, invoices.total, invoices.status, invoices.id
        FROM invoices
        LEFT JOIN clients ON invoices.client_id = clients.id
    ''')
    invoices = c.fetchall()

    conn.close()

    return render_template('list_page.html', clients=clients, invoices=invoices)

@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        contact_name = request.form.get('contact_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        account_type = request.form.get('account_type', '').strip()
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        actions = request.form.get('actions', '').strip()

        # Validation
        error = None
        import re
        if not re.match(r'^[A-Za-z ]+$', contact_name):
            error = 'Contact name is required and must contain only alphabetic characters and spaces.'
        elif phone_number and (not phone_number.isdigit()):
            error = 'Phone number must contain digits only if provided.'
        elif account_type not in ['Active', 'Deactivated']:
            error = 'Invalid account type selected.'
        elif '@' not in email or '.' not in email:
            error = 'Invalid email format.'

        if error:
            client_data = (client_id, contact_name, phone_number, account_type, company_name, email, actions)
            return render_template('edit_client.html', error=error, client=client_data)

        c.execute('''
            UPDATE clients
            SET client_name = ?, phone = ?, account_type = ?, company_name = ?, email = ?, actions = ?
            WHERE id = ?
        ''', (contact_name, phone_number, account_type, company_name, email, actions, client_id))
        conn.commit()
        conn.close()
        return redirect(url_for('list_page'))
    else:
        c.execute('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ?', (client_id,))
        client = c.fetchone()
        conn.close()
        if client:
            return render_template('edit_client.html', client=client)
        else:
            return redirect(url_for('list_page'))

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_page'))

@app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        product = request.form.get('product', '').strip()
        quantity = request.form.get('quantity', '0').strip()
        price = request.form.get('price', '0').strip()
        gst = request.form.get('gst', '0').strip()
        discount = request.form.get('discount', '0').strip()
        status = request.form.get('status', '').strip()

        # Validation
        error = None
        try:
            quantity_val = int(quantity)
            price_val = float(price)
            gst_val = float(gst)
            discount_val = float(discount)
        except ValueError:
            error = 'Quantity, price, GST, and discount must be numeric.'

        if error:
            c.execute('SELECT id, client_id, product, quantity, price, gst, discount, total, status FROM invoices WHERE id = ?', (invoice_id,))
            invoice = c.fetchone()
            return render_template('edit_invoice.html', error=error, invoice=invoice)

        total = quantity_val * price_val + gst_val - discount_val

        c.execute('''
            UPDATE invoices
            SET product = ?, quantity = ?, price = ?, gst = ?, discount = ?, total = ?, status = ?
            WHERE id = ?
        ''', (product, quantity_val, price_val, gst_val, discount_val, total, status, invoice_id))
        conn.commit()
        conn.close()
        return redirect(url_for('list_page'))
    else:
        c.execute('SELECT id, client_id, product, quantity, price, gst, discount, total, status FROM invoices WHERE id = ?', (invoice_id,))
        invoice = c.fetchone()
        conn.close()
        if invoice:
            return render_template('edit_invoice.html', invoice=invoice)
        else:
            return redirect(url_for('list_page'))

@app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_page'))

from calendar import monthrange, Calendar
import datetime


# Calendar main view
@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar(year=None, month=None):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    today = datetime.date.today()
    if not year or not month:
        year = today.year
        month = today.month

    # Get jobs with client names
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT j.id, j.client_id, c.client_name, j.job_date, j.status, j.job_date, j.status, j.client_id
        FROM jobs j
        JOIN clients c ON j.client_id = c.id
        ORDER BY j.job_date
    ''')
    jobs = c.fetchall()
    conn.close()

    job_map = {}
    for job in jobs:
        job_date = job[3]
        try:
            job_dt = datetime.datetime.strptime(job_date, '%Y-%m-%d').date()
            job_map[job_dt] = {
                'id': job[0],
                'title': job[2],
                'status': 'red' if job[4] == 'Not Completed' else ('green' if job[4] == 'Completed' else 'orange'),
                'client_id': job[7]
            }
        except:
            pass

    cal = Calendar(firstweekday=0) # Monday
    month_days = cal.monthdayscalendar(year, month)
    calendar_weeks = []
    for week in month_days:
        week_cells = []
        for day in week:
            in_month = day != 0
            job = None
            if in_month:
                date_obj = datetime.date(year, month, day)
                job = job_map.get(date_obj)
            week_cells.append({'day': day if in_month else 0, 'in_month': in_month, 'job': job})
        calendar_weeks.append(week_cells)

    prev_month = month - 1
    prev_year = year
    next_month = month + 1
    next_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    if next_month > 12:
        next_month = 1
        next_year += 1

    current_month_name = datetime.date(year, month, 1).strftime('%B')

    return render_template('calendar.html',
        calendar_weeks=calendar_weeks,
        current_month_name=current_month_name,
        current_year=year,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year
    )

@app.route('/calendar/tasks', methods=['GET'])
def calendar_tasks():
    if 'user_name' not in session:
        return json.dumps([])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT j.id, c.client_name, j.job_date, j.status, j.client_id
        FROM jobs j
        JOIN clients c ON j.client_id = c.id
        ORDER BY j.job_date
    ''')
    jobs = c.fetchall()
    conn.close()
    # Map status to color and text
    def status_map(status):
        if status == 'Not Completed':
            return ('red', 'Not Completed')
        elif status == 'Completed':
            return ('green', 'Completed')
        else:
            return ('orange', 'In Progress')
    result = []
    for job in jobs:
        color, status_text = status_map(job[3])
        result.append({
            'id': job[0],
            'title': job[1],
            'date': job[2],
            'location': '',
            'status': color,
            'statusText': status_text,
            'avatar': 'https://randomuser.me/api/portraits/men/32.jpg'
        })
    return json.dumps(result)
@app.route('/calendar/add', methods=['POST'])
def calendar_add():
    if 'user_name' not in session:
        return redirect(url_for('login'))
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        time = request.form.get('time')
        location = request.form.get('location')
        status = request.form.get('status', 'Not Completed')
        client_id = request.form.get('client_id', None)
        job_date = date
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO jobs (client_id, job_date, status)
            VALUES (?, ?, ?)
        ''', (client_id, job_date, status))
        conn.commit()
        conn.close()
        return {'success': True}

# Edit event (job)
@app.route('/calendar/edit/<int:job_id>', methods=['POST'])
def calendar_edit(job_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        time = request.form.get('time')
        location = request.form.get('location')
        status = request.form.get('status', 'Not Completed')
        client_id = request.form.get('client_id', None)
        job_date = date
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''
            UPDATE jobs SET client_id=?, job_date=?, status=? WHERE id=?
        ''', (client_id, job_date, status, job_id))
        conn.commit()
        conn.close()
        return {'success': True}

# Delete event (job)
@app.route('/calendar/delete/<int:job_id>', methods=['POST'])
def calendar_delete(job_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM jobs WHERE id=?', (job_id,))
    conn.commit()
    conn.close()
    return {'success': True}

@app.route('/calendar/events')
def calendar_events():
    if 'user_name' not in session:
        return jsonify([])
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT j.id, j.client_id, c.client_name, j.job_date, j.status
        FROM jobs j
        JOIN clients c ON j.client_id = c.id
        ORDER BY j.job_date
    ''')
    jobs = c.fetchall()
    
    events = []
    for job in jobs:
        job_id, client_id, client_name, job_date, status = job
        
        # Color based on status
        if status == "Scheduled":
            color = "#ff4444"
        elif status == "In Progress":
            color = "#ffaa00"
        else:
            color = "#44ff44"
            
        events.append({
            "id": job_id,
            "title": f"{client_name} - {status}",
            "start": job_date,
            "color": color,
            "extendedProps": {
                "client_name": client_name,
                "status": status
            }
        })
    
    conn.close()
    return jsonify(events)

@app.route('/calendar/update_date', methods=["POST"])
def update_job_date():
    if 'user_name' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    job_id = data.get("id")
    new_date = data.get("date")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE jobs SET job_date = ? WHERE id = ?", (new_date, job_id))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

@app.route('/calendar/job_details/<int:job_id>')
def calendar_job_details(job_id):
    if 'user_name' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT j.id, j.client_id, c.client_name, j.job_date, j.status
        FROM jobs j
        JOIN clients c ON j.client_id = c.id
        WHERE j.id = ?
    ''', (job_id,))
    job = c.fetchone()
    
    conn.close()
    
    if job:
        return jsonify({
            "job_id": job[0],
            "client_name": job[2],
            "job_date": job[3],
            "job_status": job[4]
        })
    
    return jsonify({"error": "Job not found"}), 404


# Products List Page (should be after app initialization and with other routes)
@app.route('/products-list')
def products_list():
    return render_template('products_list.html')

if __name__ == '__main__':
    app.run(debug=True)

# --- Products Page Route ---
from flask import flash

# Allowed turf types for dropdown
ALLOWED_TURF_TYPES = [
    "Golden Imperial Lush",
    "Golden Green Lush",
    "Golden Natural 40mm",
    "Golden Golf Turf",
    "Golden Premium Turf"
]

# In-memory product list (replace with DB in production)
products = []

@app.route('/products', methods=['GET', 'POST'])
def products_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        turf_type = request.form.get('turf_type')
        description = request.form.get('description', '')
        stock = request.form.get('stock', '')

        # Validation
        c.execute('SELECT 1 FROM products WHERE LOWER(product_name) = ?', (product_name.lower(),))
        exists = c.fetchone()
        if not product_name:
            flash("Please enter the product name")
        elif exists:
            flash("Product name must be unique")
        elif turf_type not in ALLOWED_TURF_TYPES:
            flash("Invalid turf type selected")
        elif stock and (not stock.isdigit() or int(stock) < 0):
            flash("Stock amount must be a non-negative number")
        else:
            c.execute('''
                INSERT INTO products (product_name, turf_type, description, stock)
                VALUES (?, ?, ?, ?)
            ''', (product_name, turf_type, description, int(stock) if stock else None))
            conn.commit()
            flash("Product added successfully")
            return redirect('/products')
    c.execute('SELECT product_name, turf_type, description, stock FROM products')
    products = [dict(product_name=row[0], turf_type=row[1], description=row[2], stock=row[3]) for row in c.fetchall()]
    conn.close()
    return render_template('products.html', products=products, turf_types=ALLOWED_TURF_TYPES)
