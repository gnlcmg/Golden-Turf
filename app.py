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

@app.route('/payments')
def payments():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    # Fetch invoices with products and amounts
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT i.id, i.client_id, c.client_name, i.status, i.due_date, i.amount_gst, i.total_amount
        FROM invoices i
        JOIN clients c ON i.client_id = c.id
    ''')
    invoices_raw = c.fetchall()

    invoices = []
    for inv in invoices_raw:
        invoice_id, client_id, client_name, status, due_date, amount_gst, total_amount = inv

        # Fetch products for this invoice
        c.execute('SELECT name, quantity FROM invoice_products WHERE invoice_id = ?', (invoice_id,))
        products = [{"name": row[0], "quantity": row[1]} for row in c.fetchall()]

        invoices.append({
            "id": invoice_id,
            "client_name": client_name,
            "status": status,
            "due_date": due_date,
            "products": products,
            "amount_gst": amount_gst,
            "total_amount": total_amount
        })
    
    conn.close()

    current_date = datetime.today().strftime("%Y-%m-%d")
    return render_template('payments.html', invoices=invoices, current_date=current_date)

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

            c.execute('''
                INSERT INTO invoices (client_id, product, quantity, price, gst, total, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (client_id, turf_type, area_val, extra_fee_val, gst_amount, total, payment_status))
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

@app.route('/list')
def list_page():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, client_name, phone, created_date, "Active" as status FROM clients')
    clients = c.fetchall()
    c.execute('''
        SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
               invoices.gst, invoices.total, invoices.status, invoices.id
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
        status = request.form.get('status', '').strip()

        error = None
        try:
            quantity_val = int(quantity)
            price_val = float(price)
            gst_val = float(gst)
        except ValueError:
            error = 'Quantity, price, GST must be numeric.'

        if error:
            c.execute('SELECT id, client_id, product, quantity, price, gst, total, status FROM invoices WHERE id = ?', (invoice_id,))
            invoice = c.fetchone()
            return render_template('edit_invoice.html', error=error, invoice=invoice)

        total = quantity_val * price_val + gst_val

        c.execute('''
            UPDATE invoices
            SET product = ?, quantity = ?, price = ?, gst = ?, total = ?, status = ?
            WHERE id = ?
        ''', (product, quantity_val, price_val, gst_val, total, status, invoice_id))
        conn.commit()
        conn.close()
        return redirect(url_for('list_page'))
    else:
        c.execute('SELECT id, client_id, product, quantity, price, gst, total, status FROM invoices WHERE id = ?', (invoice_id,))
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

@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar(year=None, month=None):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    today = datetime.now().date()
    if not year or not month:
        year = today.year
        month = today.month

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

@app.route('/products_list', endpoint='products_list')
def products_list():
    return render_template('products_list.html', products=products)

from flask import flash

ALLOWED_TURF_TYPES = [
    "Golden Imperial Lush",
    "Golden Green Lush",
    "Golden Natural 40mm",
    "Golden Golf Turf",
    "Golden Premium Turf"
]

products = []

@app.route('/products', methods=['GET', 'POST'])
def products_page():
    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        turf_type = request.form.get('turf_type')
        description = request.form.get('description', '')
        stock = request.form.get('stock', '')

        if not product_name:
            flash("Please enter the product name")
        elif any(p['product_name'].lower() == product_name.lower() for p in products):
            flash("Product name must be unique")
        elif turf_type not in ALLOWED_TURF_TYPES:
            flash("Invalid turf type selected")
        elif stock and (not stock.isdigit() or int(stock) < 0):
            flash("Stock amount must be a non-negative number")
        else:
            products.append({
                'product_name': product_name,
                'turf_type': turf_type,
                'description': description,
                'stock': int(stock) if stock else None
            })
            flash("Product added successfully")
            return redirect('/products')
    return render_template('products.html', products=products, turf_types=ALLOWED_TURF_TYPES)

@app.route('/submit_invoice', methods=['POST'])
def submit_invoice():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    client_id = request.form.get('client_id', '').strip()
    product = request.form.get('product', '').strip()
    quantity = request.form.get('quantity', '0').strip()
    price = request.form.get('price', '0').strip()
    gst = request.form.get('gst', '0').strip()
    status = request.form.get('status', '').strip()

    error = None
    try:
        quantity_val = int(quantity)
        price_val = float(price)
        gst_val = float(gst)
    except ValueError:
        error = 'Quantity, price, and GST must be numeric.'

    if error:
        return render_template('invoice.html', error=error)

    total = quantity_val * price_val + gst_val

    c.execute('SELECT MAX(id) FROM invoices')
    max_id = c.fetchone()[0]
    invoice_id = max_id + 1 if max_id else 1

    c.execute('''
        INSERT INTO invoices (client_id, product, quantity, price, gst, total, status, id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_id, product, quantity_val, price_val, gst_val, total, status, invoice_id))
    conn.commit()

    c.execute('''
        SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
               invoices.gst, invoices.total, invoices.status
        FROM invoices
        LEFT JOIN clients ON invoices.client_id = clients.id
    ''')
    invoices = c.fetchall()

    conn.close()

    return render_template('list_page.html', invoices=invoices)

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if request.method == 'POST':
        client_name = request.form.get('client_name')
        turf_type = request.form.get('turf_type')
        area_in_sqm = float(request.form.get('area_in_sqm', 0))
        other_product = request.form.get('other_products')
        custom_price = float(request.form.get('custom_price', 0))
        other_product_quantity = int(request.form.get('other_product_quantity', 1))

        if not client_name:
            return "Please enter your name", 400
        if area_in_sqm <= 0:
            return "Area must be more than zero", 400

        # Turf price lookup
        price_per_unit = {
            'Golden Imperial Lush': 15,
            'Golden Green Lush': 19,
            'Golden Natural 40mm': 17,
            'Golden Golf Turf': 22,
            'Golden Premium Turf': 20
        }.get(turf_type, 0)

        # Other product prices
        other_product_prices = {
            'Peg': 25,
            'Artificial Hedges': 10,
            'Black Pebbles': 18,
            'White Pebbles': 15,
            'Bamboo 2m': 40,
            'Bamboo 2.4m': 38,
            'Bamboo 1.8m': 38,
            'Adhesive Tape': 25
        }

        other_product_price = custom_price if other_product == 'Fountain' else other_product_prices.get(other_product, 0)
        total_other_product_price = other_product_price * other_product_quantity
        total_price = (area_in_sqm * price_per_unit) + total_other_product_price

        # Save to DB
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client = c.fetchone()
        client_id = client[0] if client else None

        if client_id:
            c.execute('''
                INSERT INTO invoices (client_id, product, quantity, price, gst, total, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (client_id, turf_type, area_in_sqm, price_per_unit, 0, total_price, 'Quote'))
            conn.commit()
        conn.close()

        return render_template("quote_success.html", client_name=client_name, total_price=total_price)

    # GET request: just show a form for creating quotes
    return render_template("quotes.html")

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

if __name__ == '__main__':
    app.run(debug=True)

app.run()