from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import re
from datetime import datetime, timedelta
from calendar import Calendar

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route('/')
def home():
    return redirect(url_for('register'))

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")
        
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters long.")
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                      (name, email, password))
            conn.commit()
            message = 'Registration successful!'
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            message = 'Email already registered!'
            conn.close()
    
    return render_template('register.html', message=message)

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

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    user_role = 'admin'
    clients = query_all_clients()
    jobs = query_all_jobs()
    payments = query_all_payments()

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)

    total_clients = len(clients)
    total_services = sum(1 for job in jobs if job[3] == 'Completed')

    total_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid')
    today_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(payment[3], '%Y-%m-%d').date() == today)
    yesterday_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(payment[3], '%Y-%m-%d').date() == yesterday)
    last_7_days_sales = sum(payment[3] for payment in payments if payment[4] == 'Paid' and datetime.strptime(payment[3], '%Y-%m-%d').date() >= last_7_days)

    upcoming_jobs = [job for job in jobs if datetime.strptime(job[2], '%Y-%m-%d').date() >= today]
    overdue_jobs = [job for job in jobs if datetime.strptime(job[2], '%Y-%m-%d').date() < today and job[3] != 'Completed']

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

def get_all_tasks():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks ORDER BY task_date, task_time')
    tasks = c.fetchall()
    conn.close()
    return tasks

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
        location TEXT,
        status TEXT NOT NULL DEFAULT 'Not completed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

migrate_clients_table()
create_tasks_table()

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
            c.execute('''INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (contact_name, email, phone_number, account_type, company_name, actions, created_date))
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
        message = 'If this email is registered, a password reset link has been sent.'
    return render_template('forgotpassword.html', message=message)

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
        payment_status = request.form.get('payment_status', '')
        gst = request.form.get('gst', 'no')
        invoice_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            area_val = float(area)
        except ValueError:
            area_val = 0.0
        try:
            extra_fee_val = float(extra_fee)
        except ValueError:
            extra_fee_val = 0.0

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client = c.fetchone()
        client_id = client[0] if client else None

        if client_id:
            price_table = {
                'Golden Imperial Lush': 15,
                'Golden Green Lush': 19,
                'Golden Natural 40mm': 17,
                'Golden Golf Turf': 22,
                'Golden Premium Turf': 20,
                'Peg (Upins/Nails)': 25 / 100,
                'Artificial Hedges': 10 / 0.25,
                'Black Pebbles': 18 / 20,
                'White Pebbles': 15 / 20,
                'Bamboo Products': {
                    '2 metres': 40,
                    '2.4 metres': 38,
                    '1.8 metres': 38
                },
                'Adhesive Joining Tape': 25 / 15
            }

            if turf_type in price_table:
                price_per_unit = price_table[turf_type]
            elif extras in price_table:
                price_per_unit = price_table[extras]
            elif extras == 'Fountain':
                price_per_unit = 0
            else:
                price_per_unit = 0

            subtotal = area_val * price_per_unit + extra_fee_val
            gst_amount = subtotal * 0.10 if gst == 'yes' else 0
            total = subtotal + gst_amount

            c.execute('''INSERT INTO invoices (client_id, product, quantity, price, gst, total, status)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                          (client_id, turf_type, area_val, extra_fee_val, gst_amount, total, payment_status))
            conn.commit()
            conn.close()
            success = 'Invoice saved successfully.'
        else:
            success = None

        return render_template('invoice.html',
                               client_name=client_name,
                               turf_type=turf_type,
                               area=area_val,
                               extra_fee=extra_fee_val,
                               extras=extras,
                               payment_status=payment_status,
                               gst=gst,
                               invoice_id='INV-0001',
                               invoice_date=invoice_date,
                               success=success)
    else:
        return render_template('invoice.html')

@app.route('/products_list')
def products_list():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    # Get products from database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT product_name, turf_type, description, stock FROM products')
    products = c.fetchall()
    conn.close()

    return render_template('products_list.html', products=products)

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Handle form submission
        client_name = request.form.get('client_name')
        turf_type = request.form.get('turf_type')
        area_in_sqm = request.form.get('area_in_sqm')
        other_products = request.form.get('other_products')
        # Process the quote data here
        return render_template('quotes.html', success=True)
    
    return render_template('quotes.html')

@app.route('/payments')
def payments():
    """Render the blank payments page."""
    return render_template('payments.html')
def payments():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    
    # Get invoices data for payments
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date, 
                  invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id''')
    invoices_data = c.fetchall()
    conn.close()
    
    # Format the data for the template
    invoices = []
    for invoice in invoices_data:
        invoices.append({
            'client_name': invoice[1],
            'status': invoice[2],
            'due_date': invoice[3],
            'products': [{'name': invoice[4], 'quantity': invoice[5]}],
            'amount_gst': invoice[7],
            'total_amount': invoice[8]
        })
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('payments.html', invoices=invoices, current_date=current_date)

@app.route('/calendar')
def calendar():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    
    # Get current date for calendar navigation
    today = datetime.now()
    current_year = request.args.get('year', today.year, type=int)
    current_month = request.args.get('month', today.month, type=int)
    current_day = request.args.get('day', today.day, type=int)
    view = request.args.get('view', 'month')
    
    # Create current date object
    current_date = datetime(current_year, current_month, current_day)
    
    # Calculate navigation based on view
    if view == 'week':
        # Weekly navigation
        prev_date = current_date - timedelta(weeks=1)
        next_date = current_date + timedelta(weeks=1)
        
        prev_year = prev_date.year
        prev_month = prev_date.month
        prev_day = prev_date.day
        
        next_year = next_date.year
        next_month = next_date.month
        next_day = next_date.day
        
        # Get week range (Monday to Sunday)
        start_of_week = current_date - timedelta(days=current_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
    # Fetch tasks from the database for the calendar view
    tasks = get_all_tasks()  # New function to fetch tasks
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
    
    def get_ordinal_suffix(day):
        if 11 <= day <= 13:
            return 'th'
        else:
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    if view == 'week':
        start_suffix = get_ordinal_suffix(start_of_week.day)
        end_suffix = get_ordinal_suffix(end_of_week.day)
        
        if start_of_week.month == end_of_week.month and start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix} - {end_of_week.day}{end_suffix})"
        elif start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
        else:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
        
        # Generate week days
        calendar_weeks = [[(start_of_week + timedelta(days=i)).day for i in range(7)]]
        
    elif view == 'day':
        # Daily navigation
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
        
        prev_year = prev_date.year
        prev_month = prev_date.month
        prev_day = prev_date.day
        
        next_year = next_date.year
        next_month = next_date.month
        next_day = next_date.day
        
        # Format header for daily view
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        header_text = f"{month_names[current_month - 1]} {current_day}"
        
        # Generate single day
        calendar_weeks = [[current_day]]
        
    else:
        # Monthly navigation
        prev_month = current_month - 1
        prev_year = current_year
        if prev_month < 1:
            prev_month = 12
            prev_year = current_year - 1
            
        next_month = current_month + 1
        next_year = current_year
        if next_month > 12:
            next_month = 1
            next_year = current_year + 1
        
        prev_day = current_day
        next_day = current_day
        
        # Format header for monthly view
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        header_text = month_names[current_month - 1]
        
        # Generate month calendar
        cal = Calendar()
        calendar_weeks = cal.monthdayscalendar(current_year, current_month)
    
    return render_template('calendar.html', 
                          current_year=current_year,
                          current_month=current_month,
                          current_day=current_day,
                          current_month_name=header_text,
                          prev_year=prev_year,
                          prev_month=prev_month,
                          prev_day=prev_day,
                          next_year=next_year,
                          next_month=next_month,
                          next_day=next_day,
                          view=view,
                          calendar_weeks=calendar_weeks)

@app.route('/list')
def list_page():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, client_name, phone, created_date, "Active" as status FROM clients')
    clients = c.fetchall()
    c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
                  invoices.gst, invoices.total, invoices.status, invoices.id
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id''')
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
        account_type = request.form.get('account_type', '')
        company_name = request.form.get('company_name', '')
        email = request.form.get('email', '')
        # Additional logic for editing client
        # ...
        conn.commit()
    return render_template('edit_client.html')

# Task management API endpoints
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
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
            'location': task[5],
            'status': task[6],
            'created_at': task[7]
        })
    
    return jsonify(task_list)

@app.route('/api/tasks', methods=['POST'])
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
    location = data.get('location', '')
    status = data.get('status', 'Not completed')
    
    if not title or not task_date:
        print("Task creation failed: Title and date are required.")
        return jsonify({'error': 'Title and date are required'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO tasks (title, description, task_date, task_time, location, status)
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                     (title, description, task_date, task_time, location, status))
        task_id = c.lastrowid  # Get the ID of the newly added task
        conn.commit()
        print(f"Task added successfully: {title} with ID {task_id}.")
        conn.close()
    except Exception as e:
        print(f"Error adding task: {str(e)}")
        conn.close()
        return jsonify({'error': 'Failed to add task'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    task_date = data.get('date')
    task_time = data.get('time', '')
    location = data.get('location', '')
    status = data.get('status', 'Not completed')
    
    if not title or not task_date:
        return jsonify({'error': 'Title and date are required'}), 400
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''UPDATE tasks SET title=?, description=?, task_date=?, task_time=?, location=?, status=?
                 WHERE id=?''', 
                 (title, description, task_date, task_time, location, status, task_id))
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

if __name__ == "__main__":
    app.run(debug=True)