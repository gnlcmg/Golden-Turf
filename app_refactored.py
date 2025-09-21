"""
Refactored Golden Turf Flask Application
This version includes security fixes, proper configuration, and modular structure.
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mail import Mail, Message
from flask_cors import CORS
import os
from datetime import datetime, timedelta
from calendar import Calendar

# Import our custom modules
from config import get_config
from utils.database import get_db
from utils.security import get_security

# Initialize Flask app
app = Flask(__name__)
config = get_config()
app.config.from_object(config)

# Initialize extensions
mail = Mail(app)
CORS(app, supports_credentials=True)

# Initialize utilities
db = get_db()
security = get_security()

def has_permission(module):
    """
    Check if the current user has permission for a specific module.
    Returns True if user is admin, user_id is 1, or has specific permission.
    """
    if 'user_role' not in session:
        return False

    # Admin users have access to everything
    if session.get('user_role') == 'admin':
        return True

    # User ID 1 always has access
    if session.get('user_id') == 1:
        return True

    # Check specific permissions
    user_permissions = session.get('user_permissions', '')
    if not user_permissions:
        return False

    # Permissions are stored as comma-separated string
    permissions_list = [p.strip() for p in user_permissions.split(',') if p.strip()]
    return module in permissions_list

@app.route('/')
def home():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = security.sanitize_input(request.form.get('name', ''))
        email = security.sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '').strip()

        # Validate input
        if not name or not email or not password:
            flash('All fields are required.')
            return render_template('register.html')

        # Validate email format
        if not security.validate_email(email):
            flash('Please enter a valid email address.')
            return render_template('register.html')

        # Validate password strength
        is_valid, password_message = security.validate_password_strength(password)
        if not is_valid:
            flash(password_message)
            return render_template('register.html')

        # Check if password is compromised
        if security.is_password_compromised(password):
            flash('This password is too common. Please choose a different password.')
            return render_template('register.html')

        # Hash the password
        hashed_password = security.hash_password(password)

        try:
            # Create user in database
            db.create_user(name, email, hashed_password, 'user')
            flash('Registration successful!')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = security.sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please enter email and password.')
            return render_template('login.html')

        # Validate email format
        if not security.validate_email(email):
            flash('Please enter a valid email address.')
            return render_template('login.html')

        # Get user from database
        user = db.get_user_by_email(email)

        if user and security.verify_password(password, user[3]):  # user[3] is password
            # Set session variables
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_role'] = user[4] if user[4] else 'user'
            session['user_permissions'] = user[5] if user[5] else ''

            # Create user-specific database if it doesn't exist
            user_db_path = f'{email.replace("@", "_").replace(".", "_")}_db.sqlite'
            session['database'] = user_db_path

            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Get dashboard data using database utilities
    clients = db.get_all_clients(user_id)
    # Note: Other dashboard data would need similar treatment

    return render_template('dashboard.html',
                          total_clients=len(clients),
                          user_role=session.get('user_role', 'user'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/access_restricted')
def access_restricted():
    if 'user_name' not in session:
        return redirect(url_for('login'))
    # User with ID 1 always has access
    if session.get('user_id') == 1:
        return redirect(url_for('dashboard'))
    return render_template('access_restricted.html')

# Password reset functionality
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = security.sanitize_input(request.form.get('email', ''))

        if not email:
            flash('Please enter your email address.')
            return render_template('forgotpassword.html')

        if not security.validate_email(email):
            flash('Please enter a valid email address.')
            return render_template('forgotpassword.html')

        # Check if user exists
        user = db.get_user_by_email(email)
        if user:
            # Generate verification code
            verification_code = security.generate_verification_code()
            token_expiry = security.get_token_expiry(10)  # 10 minutes

            # Update user with verification code
            db.execute_query(
                "UPDATE users SET verification_code = ?, token_expiry = ? WHERE id = ?",
                (verification_code, token_expiry, user[0]),
                commit=True
            )

            # Send email (implement email sending logic)
            # msg = Message('Your Verification Code', sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[email])
            # msg.body = f'Your verification code is: {verification_code}'
            # mail.send(msg)

            flash('If this email is registered, a verification code has been sent.')
            return redirect(url_for('verify_code', email=email))
        else:
            flash('If this email is registered, a verification code has been sent.')

    return render_template('forgotpassword.html')

@app.route('/verify_code/<email>', methods=['GET', 'POST'])
def verify_code(email):
    if request.method == 'POST':
        code = security.sanitize_input(request.form.get('code', ''))

        if not code:
            flash('Please enter the verification code.')
            return render_template('verify_code.html', email=email)

        # Get user and verify code
        user = db.get_user_by_email(email)

        if user and user[6] == code:  # user[6] is verification_code
            token_expiry = user[7]  # user[7] is token_expiry
            if not security.is_token_expired(token_expiry):
                # Successful verification
                return redirect(url_for('reset_password', email=email))
            else:
                flash('Verification code has expired.')
        else:
            flash('Invalid verification code.')

    return render_template('verify_code.html', email=email)

@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not new_password or not confirm_password:
            flash('Please fill in all fields.')
            return render_template('reset_password.html', email=email)

        if new_password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', email=email)

        # Validate password strength
        is_valid, password_message = security.validate_password_strength(new_password)
        if not is_valid:
            flash(password_message)
            return render_template('reset_password.html', email=email)

        # Check if password is compromised
        if security.is_password_compromised(new_password):
            flash('This password is too common. Please choose a different password.')
            return render_template('reset_password.html', email=email)

        # Hash the new password
        hashed_password = security.hash_password(new_password)

        # Update password in database
        user = db.get_user_by_email(email)
        if user:
            db.update_user_password(user[0], hashed_password)
            flash('Password reset successful!')
            return redirect(url_for('login'))
        else:
            flash('User not found.')

    return render_template('reset_password.html', email=email)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

if __name__ == "__main__":
    # Only run in development
    if app.config['DEBUG']:
        print("🚀 Starting Golden Turf in development mode...")
        print("📧 Email functionality requires proper SMTP configuration")
        print("🔒 Security features enabled")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Production mode - use gunicorn or similar WSGI server")
