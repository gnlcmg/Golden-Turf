"""
Security utilities for password hashing, validation, and input sanitization.
"""
import bcrypt
import re
import secrets
import string
from datetime import datetime, timedelta
from config import get_config

class SecurityManager:
    """Security utilities for the application."""

    def __init__(self):
        self.config = get_config()

    def hash_password(self, password):
        """
        Hash a password using bcrypt.

        Args:
            password (str): Plain text password

        Returns:
            str: Hashed password
        """
        if not isinstance(password, str):
            raise ValueError("Password must be a string")

        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password, hashed_password):
        """
        Verify a password against its hash.

        Args:
            password (str): Plain text password
            hashed_password (str): Hashed password

        Returns:
            bool: True if password matches
        """
        if not isinstance(password, str) or not isinstance(hashed_password, str):
            return False

        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except (ValueError, TypeError):
            return False

    def validate_password_strength(self, password):
        """
        Validate password strength.

        Args:
            password (str): Password to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"

        min_length = self.config.PASSWORD_MIN_LENGTH
        if len(password) < min_length:
            return False, f"Password must be at least {min_length} characters long"

        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        return True, "Password is strong"

    def generate_verification_code(self, length=6):
        """
        Generate a verification code for email verification.

        Args:
            length (int): Length of the code

        Returns:
            str: Verification code
        """
        return ''.join(secrets.choice('0123456789') for _ in range(length))

    def generate_reset_token(self):
        """
        Generate a secure reset token.

        Returns:
            str: Reset token
        """
        return secrets.token_urlsafe(32)

    def sanitize_input(self, input_string, max_length=255):
        """
        Sanitize user input to prevent XSS and other attacks.

        Args:
            input_string (str): Input to sanitize
            max_length (int): Maximum allowed length

        Returns:
            str: Sanitized input
        """
        if not isinstance(input_string, str):
            return ""

        # Remove potential HTML/JavaScript
        input_string = re.sub(r'<[^>]+>', '', input_string)
        input_string = re.sub(r'javascript:', '', input_string, flags=re.IGNORECASE)
        input_string = re.sub(r'on\w+\s*=', '', input_string, flags=re.IGNORECASE)

        # Trim whitespace and limit length
        input_string = input_string.strip()[:max_length]

        return input_string

    def validate_email(self, email):
        """
        Validate email address format.

        Args:
            email (str): Email to validate

        Returns:
            bool: True if valid
        """
        if not email:
            return False

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))

    def validate_phone(self, phone):
        """
        Validate phone number format.

        Args:
            phone (str): Phone number to validate

        Returns:
            bool: True if valid
        """
        if not phone:
            return True  # Phone is optional

        # Allow digits, spaces, hyphens, parentheses, and plus sign
        phone_pattern = r'^[\d\s\-\(\)\+]+$'
        return bool(re.match(phone_pattern, phone.strip()))

    def is_password_compromised(self, password):
        """
        Check if password is in common compromised passwords list.
        This is a basic check - in production, use HaveIBeenPwned API.

        Args:
            password (str): Password to check

        Returns:
            bool: True if compromised
        """
        # Common weak passwords
        compromised_passwords = {
            'password', 'password123', '123456', '123456789', 'qwerty',
            'abc123', 'password1', 'admin', 'letmein', 'welcome',
            'monkey', '1234567890', 'iloveyou', 'princess', 'rockyou'
        }

        return password.lower() in compromised_passwords

    def get_token_expiry(self, hours=24):
        """
        Get token expiry time.

        Args:
            hours (int): Hours until expiry

        Returns:
            str: Expiry time in string format
        """
        expiry_time = datetime.now() + timedelta(hours=hours)
        return expiry_time.strftime('%Y-%m-%d %H:%M:%S')

    def is_token_expired(self, token_expiry):
        """
        Check if token is expired.

        Args:
            token_expiry (str): Token expiry time

        Returns:
            bool: True if expired
        """
        try:
            expiry_time = datetime.strptime(token_expiry, '%Y-%m-%d %H:%M:%S')
            return datetime.now() > expiry_time
        except (ValueError, TypeError):
            return True  # If we can't parse, consider it expired

# Global security manager instance
security_manager = SecurityManager()

def get_security():
    """Get security manager instance."""
    return security_manager
