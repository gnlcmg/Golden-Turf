"""
Database utility functions for secure and efficient database operations.
"""
import sqlite3
import os
import functools
from contextlib import contextmanager
from config import get_config

class DatabaseManager:
    """Database connection manager with connection pooling and security."""

    def __init__(self):
        self.config = get_config()
        self.db_path = self._get_database_path()

    def _get_database_path(self):
        """Get database path from configuration."""
        db_uri = self.config.DATABASE_URI
        return db_uri.replace('sqlite:///', '')

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper configuration."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable security and performance features
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            conn.execute("PRAGMA synchronous = NORMAL")  # Better performance
            conn.execute("PRAGMA cache_size = 10000")  # 10MB cache
            conn.execute("PRAGMA temp_store = memory")
            conn.execute("PRAGMA mmap_size = 268435456")  # 256MB memory map

            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def execute_query(self, query, params=None, fetchone=False, fetchall=False, commit=False):
        """
        Execute a database query safely with parameterized statements.

        Args:
            query (str): SQL query with ? placeholders
            params (tuple): Parameters for the query
            fetchone (bool): Return single row
            fetchall (bool): Return all rows
            commit (bool): Commit the transaction

        Returns:
            Result of the query based on fetch parameters
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            if params:
                c.execute(query, params)
            else:
                c.execute(query)

            if commit:
                conn.commit()

            if fetchone:
                return c.fetchone()
            elif fetchall:
                return c.fetchall()
            else:
                return c.lastrowid if commit else None

    def execute_many(self, query, params_list, commit=True):
        """
        Execute multiple queries efficiently.

        Args:
            query (str): SQL query with ? placeholders
            params_list (list): List of parameter tuples
            commit (bool): Commit the transaction
        """
        with self.get_connection() as conn:
            c = conn.cursor()
            c.executemany(query, params_list)
            if commit:
                conn.commit()

    def get_user_by_email(self, email):
        """Get user by email address."""
        return self.execute_query(
            "SELECT id, name, email, password, role, permissions FROM users WHERE email = ?",
            (email,),
            fetchone=True
        )

    def get_user_by_id(self, user_id):
        """Get user by ID."""
        return self.execute_query(
            "SELECT id, name, email, password, role, permissions FROM users WHERE id = ?",
            (user_id,),
            fetchone=True
        )

    def create_user(self, name, email, hashed_password, role='user'):
        """Create a new user."""
        try:
            return self.execute_query(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, hashed_password, role),
                commit=True
            )
        except sqlite3.IntegrityError:
            raise ValueError("Email already exists")

    def update_user_password(self, user_id, hashed_password):
        """Update user password."""
        return self.execute_query(
            "UPDATE users SET password = ? WHERE id = ?",
            (hashed_password, user_id),
            commit=True
        )

    def get_all_clients(self, owner_id):
        """Get all clients for a user."""
        return self.execute_query(
            "SELECT * FROM clients WHERE owner_id = ?",
            (owner_id,),
            fetchall=True
        )

    def create_client(self, client_data, owner_id):
        """Create a new client."""
        query = """
            INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            client_data['client_name'],
            client_data.get('email', ''),
            client_data.get('phone', ''),
            client_data.get('account_type', 'Active'),
            client_data.get('company_name', ''),
            client_data.get('actions', ''),
            client_data.get('created_date', ''),
            owner_id
        )
        return self.execute_query(query, params, commit=True)

    def get_all_invoices(self, owner_id):
        """Get all invoices for a user."""
        return self.execute_query(
            """
            SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date,
                   invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.extras_json
            FROM invoices
            LEFT JOIN clients ON invoices.client_id = clients.id
            WHERE invoices.owner_id = ?
            """,
            (owner_id,),
            fetchall=True
        )

    def create_invoice(self, invoice_data, owner_id):
        """Create a new invoice."""
        query = """
            INSERT INTO invoices (client_id, product, quantity, price, gst, total, status, created_date, extras_json, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        """
        params = (
            invoice_data['client_id'],
            invoice_data['product'],
            invoice_data['quantity'],
            invoice_data['price'],
            invoice_data['gst'],
            invoice_data['total'],
            invoice_data['status'],
            invoice_data.get('extras_json', ''),
            owner_id
        )
        return self.execute_query(query, params, commit=True)

    def get_all_tasks(self, owner_id=None):
        """Get all tasks for a user."""
        if owner_id:
            return self.execute_query(
                "SELECT * FROM tasks WHERE owner_id = ? ORDER BY task_date, task_time",
                (owner_id,),
                fetchall=True
            )
        else:
            return self.execute_query(
                "SELECT * FROM tasks ORDER BY task_date, task_time",
                fetchall=True
            )

    def create_task(self, task_data, owner_id):
        """Create a new task."""
        query = """
            INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task_data['title'],
            task_data.get('description', ''),
            task_data['task_date'],
            task_data.get('task_time', ''),
            task_data.get('task_end_time', ''),
            task_data.get('location', ''),
            task_data.get('status', 'Not completed'),
            task_data.get('assigned_user_id'),
            owner_id
        )
        return self.execute_query(query, params, commit=True)

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Get database manager instance."""
    return db_manager

def safe_query(func):
    """Decorator for safe database operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            print(f"Database error in {func.__name__}: {e}")
            raise e
    return wrapper
