"""
Golden Turf Management System - Flask Application
Main application file for Golden Turf business management system.

This application provides:
- User authentication and session management
- Client and product management
- Invoice and payment tracking
- Calendar scheduling for jobs
- Dashboard with business analytics

Author: Golden Turf Development Team
Version: 1.0.0
"""

# Standard library imports
import sqlite3
import json
import re
from datetime import datetime, timedelta
from calendar import monthrange, Calendar

# Third-party imports
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Initialize Flask application
application = Flask(__name__)
application.secret_key = 'your_secure_secret_key_here'  # TODO: Replace with environment variable in production

# Database configuration
DATABASE_NAME = 'users.db'

# Constants
ALLOWED_TURF_TYPES = [
    "Golden Imperial Lush",
    "Golden Green Lush",
    "Golden Natural 40mm",
    "Golden Golf Turf",
    "Golden Premium Turf"
]

# In-memory product list (replace with database in production)
PRODUCTS_LIST = []

# Price configuration
TURF_PRICE_TABLE = {
    'Golden Imperial Lush': {'Small': 20, 'Medium': 30, 'Large': 40},
    'Golden Green Lush': {'Small': 18, 'Medium': 28, 'Large': 38},
    'Golden Natural 40mm': {'Small': 22, 'Medium': 32, 'Large': 42},
    'Golden Golf Turf': {'Small': 25, 'Medium': 35, 'Large': 45},
    'Golden Premium Turf': {'Small': 28, 'Medium': 38, 'Large': 48}
}

def get_database_connection():
    """Establish and return a database connection."""
    return sqlite3.connect(DATABASE_NAME)

def query_all_clients():
    """
    Retrieve all clients from the database.
    
    Returns:
        list: List of client records
    """
    connection = get_database_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM clients')
    clients = cursor.fetchall()
    connection.close()
    return clients

def query_all_jobs():
    """
    Retrieve all jobs from the database.
    
    Returns:
        list: List of job records
    """
    connection = get_database_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM jobs')
    jobs = cursor.fetchall()
    connection.close()
    return jobs

def query_all_payments():
    """
    Retrieve all payments from the database.
    
    Returns:
        list: List of payment records
    """
    connection = get极狐
