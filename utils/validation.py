"""
Input Validation Module for Golden Turf Application
==================================================

Provides comprehensive validation functions for all user inputs including
form data, database inputs, and API parameters. Implements type checking,
range validation, existence checking, and sanitization.

This module follows the naming conventions:
- snake_case for functions and variables
- PascalCase for classes
- Hungarian notation for specific parameter prefixes (str_, int_, bool_, etc.)
"""

from typing import Optional, Union, List, Dict, Any, Tuple
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import html


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, field_name: str = None):
        """
        Initialize validation error.
        
        Args:
            message (str): Error message describing the validation failure
            field_name (str, optional): Name of the field that failed validation
        """
        self.message = message
        self.field_name = field_name
        super().__init__(self.message)


class InputValidator:
    """
    Comprehensive input validation class with type checking,
    range validation, and existence checking capabilities.
    """
    
    # Regular expression patterns for validation
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    PHONE_PATTERN = re.compile(r'^[\+]?[0-9\s\-\(\)]{8,20}$')
    NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\'\.]{1,100}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    PASSWORD_PATTERN = re.compile(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]'
    )
    
    @staticmethod
    def validate_string(
        str_value: Any, 
        str_field_name: str, 
        int_min_length: int = 1, 
        int_max_length: int = 255,
        bool_required: bool = True,
        bool_allow_empty: bool = False
    ) -> str:
        """
        Validate and sanitize string input.
        
        Args:
            str_value: Value to validate
            str_field_name: Name of the field being validated
            int_min_length: Minimum allowed length
            int_max_length: Maximum allowed length
            bool_required: Whether the field is required
            bool_allow_empty: Whether empty strings are allowed
            
        Returns:
            str: Validated and sanitized string
            
        Raises:
            ValidationError: If validation fails
        """
        if str_value is None:
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return ""
            
        if not isinstance(str_value, str):
            str_value = str(str_value)
        
        # Sanitize HTML entities and strip whitespace
        str_sanitized = html.escape(str_value.strip(), quote=True)
        
        # Check if empty when not allowed
        if not str_sanitized and not bool_allow_empty:
            if bool_required:
                raise ValidationError(f"{str_field_name} cannot be empty", str_field_name)
            return ""
        
        # Check length constraints
        if len(str_sanitized) < int_min_length:
            raise ValidationError(
                f"{str_field_name} must be at least {int_min_length} characters",
                str_field_name
            )
            
        if len(str_sanitized) > int_max_length:
            raise ValidationError(
                f"{str_field_name} cannot exceed {int_max_length} characters",
                str_field_name
            )
            
        return str_sanitized
    
    @staticmethod
    def validate_integer(
        int_value: Any,
        str_field_name: str,
        int_min_value: Optional[int] = None,
        int_max_value: Optional[int] = None,
        bool_required: bool = True
    ) -> Optional[int]:
        """
        Validate integer input with range checking.
        
        Args:
            int_value: Value to validate
            str_field_name: Name of the field being validated
            int_min_value: Minimum allowed value
            int_max_value: Maximum allowed value
            bool_required: Whether the field is required
            
        Returns:
            Optional[int]: Validated integer or None if not required and empty
            
        Raises:
            ValidationError: If validation fails
        """
        if int_value is None or int_value == "":
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return None
            
        try:
            if isinstance(int_value, str):
                int_value = int_value.strip()
                if not int_value:
                    if bool_required:
                        raise ValidationError(f"{str_field_name} is required", str_field_name)
                    return None
            
            int_validated = int(int_value)
            
            # Check range constraints
            if int_min_value is not None and int_validated < int_min_value:
                raise ValidationError(
                    f"{str_field_name} must be at least {int_min_value}",
                    str_field_name
                )
                
            if int_max_value is not None and int_validated > int_max_value:
                raise ValidationError(
                    f"{str_field_name} cannot exceed {int_max_value}",
                    str_field_name
                )
                
            return int_validated
            
        except (ValueError, TypeError):
            raise ValidationError(f"{str_field_name} must be a valid integer", str_field_name)
    
    @staticmethod
    def validate_decimal(
        decimal_value: Any,
        str_field_name: str,
        decimal_min_value: Optional[Decimal] = None,
        decimal_max_value: Optional[Decimal] = None,
        int_decimal_places: int = 2,
        bool_required: bool = True
    ) -> Optional[Decimal]:
        """
        Validate decimal/float input with precision and range checking.
        
        Args:
            decimal_value: Value to validate
            str_field_name: Name of the field being validated
            decimal_min_value: Minimum allowed value
            decimal_max_value: Maximum allowed value
            int_decimal_places: Maximum number of decimal places
            bool_required: Whether the field is required
            
        Returns:
            Optional[Decimal]: Validated decimal or None if not required and empty
            
        Raises:
            ValidationError: If validation fails
        """
        if decimal_value is None or decimal_value == "":
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return None
            
        try:
            if isinstance(decimal_value, str):
                decimal_value = decimal_value.strip()
                if not decimal_value:
                    if bool_required:
                        raise ValidationError(f"{str_field_name} is required", str_field_name)
                    return None
            
            decimal_validated = Decimal(str(decimal_value))
            
            # Check decimal places
            if decimal_validated.as_tuple().exponent < -int_decimal_places:
                raise ValidationError(
                    f"{str_field_name} cannot have more than {int_decimal_places} decimal places",
                    str_field_name
                )
            
            # Check range constraints
            if decimal_min_value is not None and decimal_validated < decimal_min_value:
                raise ValidationError(
                    f"{str_field_name} must be at least {decimal_min_value}",
                    str_field_name
                )
                
            if decimal_max_value is not None and decimal_validated > decimal_max_value:
                raise ValidationError(
                    f"{str_field_name} cannot exceed {decimal_max_value}",
                    str_field_name
                )
                
            return decimal_validated
            
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f"{str_field_name} must be a valid number", str_field_name)
    
    @classmethod
    def validate_email(cls, str_email: Any, str_field_name: str = "Email") -> str:
        """
        Validate email address format.
        
        Args:
            str_email: Email to validate
            str_field_name: Name of the field being validated
            
        Returns:
            str: Validated email address
            
        Raises:
            ValidationError: If email format is invalid
        """
        str_email = cls.validate_string(str_email, str_field_name, 5, 254)
        str_email_lower = str_email.lower()
        
        if not cls.EMAIL_PATTERN.match(str_email_lower):
            raise ValidationError(f"{str_field_name} has invalid format", str_field_name)
            
        return str_email_lower
    
    @classmethod
    def validate_phone(
        cls, 
        str_phone: Any, 
        str_field_name: str = "Phone", 
        bool_required: bool = False
    ) -> Optional[str]:
        """
        Validate phone number format.
        
        Args:
            str_phone: Phone number to validate
            str_field_name: Name of the field being validated
            bool_required: Whether the field is required
            
        Returns:
            Optional[str]: Validated phone number or None if not required and empty
            
        Raises:
            ValidationError: If phone format is invalid
        """
        if not str_phone or str_phone == "":
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return None
        
        str_phone = cls.validate_string(str_phone, str_field_name, 8, 20, bool_required)
        if not str_phone:
            return None
            
        if not cls.PHONE_PATTERN.match(str_phone):
            raise ValidationError(f"{str_field_name} has invalid format", str_field_name)
            
        return str_phone
    
    @classmethod
    def validate_name(cls, str_name: Any, str_field_name: str) -> str:
        """
        Validate person or company name.
        
        Args:
            str_name: Name to validate
            str_field_name: Name of the field being validated
            
        Returns:
            str: Validated name
            
        Raises:
            ValidationError: If name format is invalid
        """
        str_name = cls.validate_string(str_name, str_field_name, 1, 100)
        
        if not cls.NAME_PATTERN.match(str_name):
            raise ValidationError(
                f"{str_field_name} can only contain letters, spaces, hyphens, apostrophes, and periods",
                str_field_name
            )
            
        return str_name.title()  # Capitalize properly
    
    @classmethod
    def validate_password(
        cls, 
        str_password: Any, 
        int_min_length: int = 8,
        bool_require_special: bool = True
    ) -> str:
        """
        Validate password strength.
        
        Args:
            str_password: Password to validate
            int_min_length: Minimum password length
            bool_require_special: Whether special characters are required
            
        Returns:
            str: Validated password
            
        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not str_password:
            raise ValidationError("Password is required", "password")
            
        if not isinstance(str_password, str):
            raise ValidationError("Password must be a string", "password")
        
        if len(str_password) < int_min_length:
            raise ValidationError(
                f"Password must be at least {int_min_length} characters long",
                "password"
            )
        
        # Check for required character types
        if not re.search(r'[a-z]', str_password):
            raise ValidationError(
                "Password must contain at least one lowercase letter",
                "password"
            )
            
        if not re.search(r'[A-Z]', str_password):
            raise ValidationError(
                "Password must contain at least one uppercase letter",
                "password"
            )
            
        if not re.search(r'\d', str_password):
            raise ValidationError(
                "Password must contain at least one digit",
                "password"
            )
            
        if bool_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', str_password):
            raise ValidationError(
                "Password must contain at least one special character",
                "password"
            )
            
        return str_password
    
    @classmethod
    def validate_date(
        cls,
        date_value: Any,
        str_field_name: str,
        str_format: str = "%Y-%m-%d",
        date_min: Optional[date] = None,
        date_max: Optional[date] = None,
        bool_required: bool = True
    ) -> Optional[date]:
        """
        Validate date input.
        
        Args:
            date_value: Date to validate (string or date object)
            str_field_name: Name of the field being validated
            str_format: Expected date format for string input
            date_min: Minimum allowed date
            date_max: Maximum allowed date
            bool_required: Whether the field is required
            
        Returns:
            Optional[date]: Validated date or None if not required and empty
            
        Raises:
            ValidationError: If date format or range is invalid
        """
        if date_value is None or date_value == "":
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return None
        
        if isinstance(date_value, date):
            date_validated = date_value
        elif isinstance(date_value, datetime):
            date_validated = date_value.date()
        else:
            try:
                date_validated = datetime.strptime(str(date_value).strip(), str_format).date()
            except ValueError:
                raise ValidationError(
                    f"{str_field_name} must be in format {str_format}",
                    str_field_name
                )
        
        # Check date range constraints
        if date_min is not None and date_validated < date_min:
            raise ValidationError(
                f"{str_field_name} cannot be before {date_min}",
                str_field_name
            )
            
        if date_max is not None and date_validated > date_max:
            raise ValidationError(
                f"{str_field_name} cannot be after {date_max}",
                str_field_name
            )
            
        return date_validated
    
    @staticmethod
    def validate_choice(
        choice_value: Any,
        list_valid_choices: List[Any],
        str_field_name: str,
        bool_required: bool = True
    ) -> Any:
        """
        Validate that input is one of the allowed choices.
        
        Args:
            choice_value: Value to validate
            list_valid_choices: List of valid choices
            str_field_name: Name of the field being validated
            bool_required: Whether the field is required
            
        Returns:
            Any: Validated choice value
            
        Raises:
            ValidationError: If choice is not in valid options
        """
        if choice_value is None or choice_value == "":
            if bool_required:
                raise ValidationError(f"{str_field_name} is required", str_field_name)
            return None
        
        if choice_value not in list_valid_choices:
            str_choices = ", ".join(str(choice) for choice in list_valid_choices)
            raise ValidationError(
                f"{str_field_name} must be one of: {str_choices}",
                str_field_name
            )
            
        return choice_value


# Global validator instance
input_validator = InputValidator()


def get_validator() -> InputValidator:
    """
    Get the global input validator instance.
    
    Returns:
        InputValidator: The application's input validator
    """
    return input_validator