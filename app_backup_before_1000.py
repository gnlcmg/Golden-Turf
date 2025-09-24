"""
Golden Turf Flask Application - Business management with VCE 3/4 concepts
"""
# Core Imports
from typing import Optional, Dict, List, Tuple, Any, Union, Protocol, ClassVar
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mail import Mail, Message
from flask_cors import CORS
from bcrypt import hashpw, gensalt, checkpw
import sqlite3
import re
import string
import secrets
from datetime import datetime, timedelta
from calendar import Calendar
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import defaultdict, namedtuple
import threading
import queue
import json
import logging

# Application Configuration  
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Extensions
mail_service = Mail(app)
cors_handler = CORS(app, supports_credentials=True)
app.config['MAIL_SUPPRESS_SEND'] = True

# Permission Management
def has_permission(str_module_name: str) -> bool:
    """Check if current user has permission for specific module"""
    if not isinstance(str_module_name, str) or not str_module_name.strip():
        return False
        
    if 'user_role' not in session:
        return False
        
    current_user_role = session.get('user_role', '')
    session_user_id = session.get('user_id', 0)
    
    if current_user_role == 'admin' or session_user_id == 1:
        return True
        
    user_permissions_string = session.get('user_permissions', '')
    if not user_permissions_string:
        return False
        
    permissions_list = [str_perm.strip() for str_perm in user_permissions_string.split(',') if str_perm.strip()]

    if str_module_name == 'products':
        LEGACY_PRODUCT_PERMISSIONS = [
            'turf_products', 'artificial_hedges', 'fountains', 
            'bamboo_products', 'pebbles', 'pegs', 'adhesive_tape'
        ]
        return any(str_permission in permissions_list for str_permission in LEGACY_PRODUCT_PERMISSIONS)

    return str_module_name in permissions_list


def can_change_role(int_current_user_id: int, int_target_user_id: int) -> bool:
    """Validate if current user can change target user's role"""
    # Type validation
    if not isinstance(int_current_user_id, int) or not isinstance(int_target_user_id, int):
        return False
        
    # Range validation - user IDs must be positive
    if int_current_user_id <= 0 or int_target_user_id <= 0:
        return False
        
    # Logic validation - users cannot change their own role
    return int_current_user_id != int_target_user_id


def can_demote_admin(int_target_user_id: int, str_new_role: str) -> bool:
    """Validate admin demotion to ensure at least one admin remains"""
    if not isinstance(int_target_user_id, int) or not isinstance(str_new_role, str):
        return False
        
    if int_target_user_id <= 0 or not str_new_role.strip():
        return False
    
    if str_new_role == 'admin':
        return True
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        conn.close()
        
        if admin_count <= 1:
            return False
        return True
    except sqlite3.Error:
        return False

class UserRole(Enum):
  
    ADMIN = "admin"
    USER = "user" 
    GUEST = "guest"
    MODERATOR = "moderator"

class TaskPriority(Enum):
   
    LOW = auto()
    MEDIUM = auto() 
    HIGH = auto()
    URGENT = auto()

@dataclass
class UserProfile:
    """    
    Advantages over regular classes:
    - Automatic __init__, __repr__, __eq__ methods
    - Type hints for all fields
    - Immutable options with frozen=True
    """
    user_id: int
    name: str
    email: str
    role: UserRole = UserRole.USER
    created_date: datetime = field(default_factory=datetime.now)
    permissions: List[str] = field(default_factory=list)
    login_count: int = 0
    last_login: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")
        if self.user_id <= 0:
            raise ValueError("User ID must be positive")

@dataclass(frozen=True) 
class SystemConstants:
    """Immutable system constants using frozen dataclass"""
    MAX_LOGIN_ATTEMPTS: ClassVar[int] = 5
    SESSION_TIMEOUT_MINUTES: ClassVar[int] = 60
    PASSWORD_MIN_LENGTH: ClassVar[int] = 8
    MAX_FILE_SIZE_MB: ClassVar[int] = 10
DatabaseResult = namedtuple('DatabaseResult', ['success', 'data', 'error_message', 'affected_rows'])
ValidationResult = namedtuple('ValidationResult', ['is_valid', 'errors', 'warnings'])

class Validatable(Protocol):
    """    
    Structural subtyping: Any class that implements validate() method
    conforms to this protocol without explicit inheritance
    """
    def validate(self) -> ValidationResult:
        """Validate the object and return validation result"""
        ...

class DatabaseOperations(ABC):
    """    
    Purpose: Define interface contract that all database operations must implement
    Ensures consistent method signatures across different database implementations
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection - must be implemented by subclasses"""
        pass
    
    @abstractmethod  
    def execute_query(self, query: str, params: Tuple = ()) -> DatabaseResult:
        """Execute database query - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close database connection - must be implemented by subclasses"""
        pass
    
    # Concrete method (can be inherited as-is)
    def log_operation(self, operation: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Database Operation: {operation}")

class CacheOperations(ABC):
    """Abstract base class for caching operations"""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
class SQLiteDatabase(DatabaseOperations):
    """    
    Inherits from DatabaseOperations abstract base class
    Provides SQLite-specific implementations of abstract methods
    """
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection = None
        self.is_connected = False
    
    def connect(self) -> bool:
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.is_connected = True
            self.log_operation(f"Connected to SQLite database: {self.database_path}")
            return True
        except sqlite3.Error as e:
            self.log_operation(f"Failed to connect: {e}")
            return False
    
    def execute_query(self, query: str, params: Tuple = ()) -> DatabaseResult:
        """Override abstract method with SQLite-specific implementation"""
        if not self.is_connected:
            return DatabaseResult(False, None, "Not connected to database", 0)
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            # Determine if query returns data
            if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
                data = cursor.fetchall()
                affected_rows = len(data)
            else:
                self.connection.commit()
                data = None
                affected_rows = cursor.rowcount
            
            self.log_operation(f"Executed query: {query[:50]}...")
            return DatabaseResult(True, data, "", affected_rows)
            
        except sqlite3.Error as e:
            return DatabaseResult(False, None, str(e), 0)
    
    def close(self) -> None:
        """Override abstract method"""
        if self.connection:
            self.connection.close()
            self.is_connected = False
            self.log_operation("Database connection closed")

class MemoryCache(CacheOperations):
    """
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
        self._lock = threading.Lock() 
    
    def get(self, key: str) -> Any:
        """Thread-safe cache retrieval"""
        with self._lock:
            if key in self._cache:
                # Check expiry
                if key in self._expiry and datetime.now() > self._expiry[key]:
                    del self._cache[key]
                    del self._expiry[key]
                    return None
                return self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Thread-safe cache storage with TTL"""
        with self._lock:
            self._cache[key] = value
            if ttl > 0:
                self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
            return True
    
    def delete(self, key: str) -> bool:
        """Thread-safe cache deletion"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._expiry:
                    del self._expiry[key]
                return True
            return False
class AdvancedUserManager:
    """
    Advanced user management with sophisticated data structures
    """
    
    def __init__(self, database: DatabaseOperations, cache: CacheOperations):
        self._database = database
        self._cache = cache
        
        self._user_profiles: Dict[int, UserProfile] = {}
        self._email_index: Dict[str, int] = {}  # Secondary index for fast email lookup
        self._role_groups: defaultdict = defaultdict(set)  # Users grouped by role
        self._login_attempts: defaultdict = defaultdict(int)  # Track failed logins
        self._session_tokens: Dict[str, UserProfile] = {}
        
        self._task_queue: queue.Queue = queue.Queue()
        self._is_processing = False
        
        self._event_log: List[Dict[str, Any]] = []
    
    def add_user(self, user_data: Dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        
        try:
            # Create user profile from data
            role = UserRole(user_data.get('role', 'user'))
            profile = UserProfile(
                user_id=user_data['user_id'],
                name=user_data['name'],
                email=user_data['email'].lower(),
                role=role,
                permissions=user_data.get('permissions', [])
            )
            
            # Validation checks
            if profile.email in self._email_index:
                errors.append("Email already exists")
            
            if profile.user_id in self._user_profiles:
                errors.append("User ID already exists")
            
            if len(errors) == 0:
                # Store in multiple data structures for efficient access
                self._user_profiles[profile.user_id] = profile
                self._email_index[profile.email] = profile.user_id
                self._role_groups[profile.role].add(profile.user_id)
                
                # Cache frequently accessed data
                cache_key = f"user_{profile.user_id}"
                self._cache.set(cache_key, profile, ttl=1800)  # 30 minutes
                
                # Log event
                self._log_event("user_created", {
                    "user_id": profile.user_id,
                    "email": profile.email,
                    "role": profile.role.value
                })
                
                return ValidationResult(True, [], warnings)
            else:
                return ValidationResult(False, errors, warnings)
                
        except ValueError as e:
            errors.append(str(e))
            return ValidationResult(False, errors, warnings)
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserProfile]:
        email = email.lower()
        
        # Rate limiting check
        if self._login_attempts[email] >= SystemConstants.MAX_LOGIN_ATTEMPTS:
            self._log_event("authentication_blocked", {"email": email, "reason": "rate_limit"})
            return None
        
        # Get user by email (O(1) lookup using index)
        user_id = self._email_index.get(email)
        if not user_id:
            self._login_attempts[email] += 1
            return None
        
        user_profile = self._user_profiles.get(user_id)
        if not user_profile:
            return None
        
        # In real implementation, verify password hash here
        # For demo purposes, assume password is valid
        
        # Reset login attempts on successful login
        if email in self._login_attempts:
            del self._login_attempts[email]
        
        # Update login statistics
        user_profile.login_count += 1
        user_profile.last_login = datetime.now()
        
        self._log_event("user_authenticated", {
            "user_id": user_id,
            "email": email,
            "login_count": user_profile.login_count
        })
        
        return user_profile
    
    def get_users_by_role(self, role: UserRole) -> List[UserProfile]:
        user_ids = self._role_groups[role]
        return [self._user_profiles[uid] for uid in user_ids if uid in self._user_profiles]
    
    def search_users(self, search_term: str, search_fields: List[str] = None) -> List[UserProfile]:
        if search_fields is None:
            search_fields = ['name', 'email']
        
        search_term = search_term.lower()
        results = []
        
        for profile in self._user_profiles.values():
            match_score = 0
            
            for field in search_fields:
                field_value = getattr(profile, field, "").lower()
                if search_term in field_value:
                    # Exact match gets higher score
                    if search_term == field_value:
                        match_score += 10
                    elif field_value.startswith(search_term):
                        match_score += 5
                    else:
                        match_score += 1
            
            if match_score > 0:
                results.append((profile, match_score))
        
        # Sort by match score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return [profile for profile, score in results]
    
    def _log_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": event_data,
            "session_id": getattr(threading.current_thread(), 'session_id', 'unknown')
        }
        self._event_log.append(event)
        
        # Keep only last 1000 events (circular buffer concept)
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]
    
    def get_user_statistics(self) -> Dict[str, Any]:
        total_users = len(self._user_profiles)
        role_distribution = {role.value: len(users) for role, users in self._role_groups.items()}
        
        # Calculate login statistics
        total_logins = sum(profile.login_count for profile in self._user_profiles.values())
        active_users = sum(1 for profile in self._user_profiles.values() 
                          if profile.last_login and 
                          profile.last_login > datetime.now() - timedelta(days=30))
        
        # Recent activity analysis
        recent_events = [event for event in self._event_log 
                        if datetime.fromisoformat(event['timestamp']) > 
                        datetime.now() - timedelta(hours=24)]
        
        return {
            "total_users": total_users,
            "role_distribution": role_distribution,
            "total_logins": total_logins,
            "active_users_30_days": active_users,
            "recent_events_24h": len(recent_events),
            "failed_login_attempts": dict(self._login_attempts),
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache performance metrics"""
        # Simplified calculation for demonstration
class NotificationStrategy(ABC):

    @abstractmethod
    def send_notification(self, recipient: str, message: str) -> bool:
        pass

class EmailNotification(NotificationStrategy):
    """Email notification implementation"""
    def send_notification(self, recipient: str, message: str) -> bool:
        # Simulate email sending
        print(f"EMAIL: Sending to {recipient}: {message}")
        return True

class SMSNotification(NotificationStrategy):
    """SMS notification implementation"""  
    def send_notification(self, recipient: str, message: str) -> bool:
        # Simulate SMS sending
        print(f"SMS: Sending to {recipient}: {message}")
        return True

class PushNotification(NotificationStrategy):
    """Push notification implementation"""
    def send_notification(self, recipient: str, message: str) -> bool:
        # Simulate push notification
        print(f"PUSH: Sending to {recipient}: {message}")
        return True

class NotificationFactory:
    _notification_types = {
        'email': EmailNotification,
        'sms': SMSNotification, 
        'push': PushNotification
    }
    
    @classmethod
    def create_notification(cls, notification_type: str) -> NotificationStrategy:
        """Create notification instance based on type - Polymorphism in action"""
        notification_class = cls._notification_types.get(notification_type.lower())
        if not notification_class:
            raise ValueError(f"Unknown notification type: {notification_type}")
        return notification_class()
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Return list of available notification types"""
        return list(cls._notification_types.keys())

class NotificationManager:

    def __init__(self):
        self._strategies: Dict[str, NotificationStrategy] = {}
        self._delivery_log: List[Dict[str, Any]] = []
    
    def add_strategy(self, name: str, strategy: NotificationStrategy) -> None:
        """Add a notification strategy - Dependency injection"""
        self._strategies[name] = strategy
    
    def send_notification(self, strategy_name: str, recipient: str, message: str) -> bool:
        """Send notification using specified strategy - Polymorphism"""
        if strategy_name not in self._strategies:
            return False
        
        strategy = self._strategies[strategy_name]
        success = strategy.send_notification(recipient, message)
        
        # Log delivery attempt
        self._delivery_log.append({
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy_name,
            'recipient': recipient,
            'success': success,
            'message_length': len(message)
        })
        
        return success
    
    def broadcast_notification(self, recipient: str, message: str) -> Dict[str, bool]:
        """Send notification via all available strategies - Polymorphism showcase"""
        results = {}
        for strategy_name, strategy in self._strategies.items():
            results[strategy_name] = strategy.send_notification(recipient, message)
        return results

vce_system_components = {
    'notification_factory': NotificationFactory(),
    'notification_manager': NotificationManager(),
    'advanced_features_active': True
}
class UserManager:
    """
    User management class demonstrating OOP principles with access modifiers.
    
    Data Types Chosen:
    - Dict for session storage: O(1) lookup performance for user data
    - Set for role validation: Fast membership testing for user roles
    - Tuple for user data: Immutable data structure for security
    
    Access Modifiers:
    - Private methods (__method): Internal implementation details
    - Protected methods (_method): For inheritance/internal use
    - Public methods (method): External interface
    """
    
    def __init__(self):
        """Initialize UserManager with private session storage."""
        # Private attributes (name mangling with __)
        self.__private_session_cache: Dict[str, Any] = {}
        self.__private_max_sessions: int = 100
        
        # Protected attributes (single underscore)
        self._protected_valid_roles: set = {'admin', 'user', 'guest'}
        self._protected_session_timeout: int = 3600  # seconds
        
        # Public attributes
        self.public_user_count: int = 0
        
    def __private_validate_user_data(self, user_data: Tuple) -> bool:
        """
        Private method for internal user data validation.
        
        Args:
            user_data (Tuple): User data tuple from database
            
        Returns:
            bool: True if user data is valid
            
        Data Structure Explanation:
        - Tuple chosen for user_data: Immutable to prevent accidental modification
        - Boolean return: Simple binary validation result
        """
        if not isinstance(user_data, tuple) or len(user_data) < 4:
            return False
        return user_data[0] is not None and user_data[1] is not None
    
    def _protected_get_session_data(self, session_key: str) -> Optional[Dict]:
        """
        Protected method for session data retrieval.
        
        Args:
            session_key (str): Unique session identifier
            
        Returns:
            Optional[Dict]: Session data or None if not found
            
        Data Source Explanation:
        - Dictionary chosen for session storage: Key-value pairs for user attributes
        - Optional return type: Handle cases where session doesn't exist
        """
        return self.__private_session_cache.get(session_key, None)
    
    def _protected_cache_user_session(self, user_id: int, session_data: Dict) -> None:
        """
        Protected method to cache user session data.
        
        Args:
            user_id (int): User identifier
            session_data (Dict): Session information to cache
            
        Data Structure Explanation:
        - Integer for user_id: Efficient database key reference
        - Dictionary for session_data: Flexible storage for various user attributes
        """
        session_key = f"user_{user_id}"
        self.__private_session_cache[session_key] = session_data.copy()
        
        # Implement cache size limit with while loop (iteration requirement)
        cache_keys = list(self.__private_session_cache.keys())
        cache_index = 0
        while len(self.__private_session_cache) > self.__private_max_sessions and cache_index < len(cache_keys):
            oldest_key = cache_keys[cache_index]
            del self.__private_session_cache[oldest_key]
            cache_index += 1
    
    def public_validate_user_session(self, user_id: int, session_data: Dict) -> bool:
        """
        Public method to validate user session with comprehensive checks.
        
        Args:
            user_id (int): User identifier for validation
            session_data (Dict): Session data to validate
            
        Returns:
            bool: True if session is valid
            
        OOP Principle: Public interface that uses private/protected methods internally
        """
        # Input validation with range checking
        if not isinstance(user_id, int) or user_id <= 0:
            return False
        
        if not isinstance(session_data, dict) or not session_data:
            return False
        
        # Use protected method to get cached session
        cached_session = self._protected_get_session_data(f"user_{user_id}")
        
        # Validate user role using protected attribute
        user_role = session_data.get('role', '')
        if user_role not in self._protected_valid_roles:
            return False
        
        # Cache valid session using protected method
        self._protected_cache_user_session(user_id, session_data)
        
        return True
    
    def public_get_user_statistics(self) -> Dict[str, Union[int, List[str]]]:
        """
        Public method to get user statistics with various data types.
        
        Returns:
            Dict[str, Union[int, List[str]]]: Statistics with mixed data types
            
        Data Types Demonstration:
        - Dict return type: Structured data with meaningful keys
        - Union type: Shows different possible value types
        - List[str]: Ordered collection of string values
        """
        active_sessions = []
        total_cached_sessions = 0
        
        # Use while loop to process cached sessions (repetition requirement)
        session_items = list(self.__private_session_cache.items())
        item_index = 0
        while item_index < len(session_items):
            session_key, session_data = session_items[item_index]
            if isinstance(session_data, dict) and session_data.get('active', False):
                active_sessions.append(session_key)
            total_cached_sessions += 1
            item_index += 1
        
        return {
            'total_sessions': total_cached_sessions,
            'active_sessions_count': len(active_sessions),
            'active_session_keys': active_sessions,
            'valid_roles': list(self._protected_valid_roles),
            'max_session_limit': self.__private_max_sessions
        }


class FormProcessor:
    """
    Form processing class representing GUI control handling.
    
    Data Sources Explanation:
    - Form data: HTTP request data from web forms (user input source)
    - Validation rules: Internal configuration data (application logic source)
    - Error messages: Static text data (internationalization source)
    """
    
    def __init__(self):
        """Initialize FormProcessor with form validation rules."""
        # Form field configurations (data structure: nested dictionaries)
        self.form_configurations: Dict[str, Dict[str, Any]] = {
            'login': {
                'fields': ['email', 'password'],
                'required': True,
                'validation_rules': {
                    'email': {'type': str, 'min_length': 5, 'max_length': 254},
                    'password': {'type': str, 'min_length': 6, 'max_length': 128}
                }
            },
            'registration': {
                'fields': ['name', 'email', 'password'],
                'required': True,
                'validation_rules': {
                    'name': {'type': str, 'min_length': 2, 'max_length': 100},
                    'email': {'type': str, 'min_length': 5, 'max_length': 254},
                    'password': {'type': str, 'min_length': 6, 'max_length': 128}
                }
            }
        }
        
        # Error message templates (data structure: dictionary for localization)
        self.error_templates: Dict[str, str] = {
            'required': '{field} is required',
            'min_length': '{field} must be at least {min_length} characters',
            'max_length': '{field} cannot exceed {max_length} characters',
            'invalid_type': '{field} must be a {expected_type}'
        }
    
    def process_form_data(self, form_type: str, form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Process and validate form data with comprehensive error handling.
        
        Args:
            form_type (str): Type of form being processed
            form_data (Dict[str, Any]): Raw form data from request
            
        Returns:
            Tuple[bool, Dict[str, List[str]]]: (is_valid, error_messages)
            
        Data Structure Explanation:
        - Tuple return: Multiple related values (validation result and errors)
        - Dict[str, List[str]]: Field names mapped to list of error messages
        - Any type: Flexible input handling for various form field types
        """
        errors: Dict[str, List[str]] = {}
        
        # Get form configuration
        form_config = self.form_configurations.get(form_type, {})
        if not form_config:
            errors['form'] = [f'Unknown form type: {form_type}']
            return False, errors
        
        # Validate each field with while loop (control structure requirement)
        field_list = form_config.get('fields', [])
        field_index = 0
        while field_index < len(field_list):
            field_name = field_list[field_index]
            field_errors = self._validate_form_field(
                field_name, 
                form_data.get(field_name), 
                form_config.get('validation_rules', {}).get(field_name, {})
            )
            
            if field_errors:
                errors[field_name] = field_errors
            
            field_index += 1
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_form_field(self, field_name: str, field_value: Any, validation_rules: Dict[str, Any]) -> List[str]:
        """
        Validate individual form field against rules.
        
        Args:
            field_name (str): Name of the field being validated
            field_value (Any): Value to validate
            validation_rules (Dict[str, Any]): Validation constraints
            
        Returns:
            List[str]: List of validation error messages
            
        Data Type Explanation:
        - List[str] for errors: Ordered collection allowing multiple error messages
        - Any for field_value: Handles various input types (str, int, bool, etc.)
        """
        field_errors: List[str] = []
        
        # Required field check
        if not field_value and validation_rules.get('required', True):
            field_errors.append(self.error_templates['required'].format(field=field_name))
            return field_errors
        
        if field_value:  # Only validate if value exists
            # Type checking
            expected_type = validation_rules.get('type', str)
            if not isinstance(field_value, expected_type):
                field_errors.append(
                    self.error_templates['invalid_type'].format(
                        field=field_name, 
                        expected_type=expected_type.__name__
                    )
                )
            
            # String length validation (range checking)
            if isinstance(field_value, str):
                min_length = validation_rules.get('min_length', 0)
                max_length = validation_rules.get('max_length', 1000)
                
                if len(field_value) < min_length:
                    field_errors.append(
                        self.error_templates['min_length'].format(
                            field=field_name, 
                            min_length=min_length
                        )
                    )
                
                if len(field_value) > max_length:
                    field_errors.append(
                        self.error_templates['max_length'].format(
                            field=field_name, 
                            max_length=max_length
                        )
                    )
        
        return field_errors


class ConfigFileManager:
    """
    Configuration file management class demonstrating additional data sources.
    
    Data Sources Implemented:
    - JSON files: Structured configuration data (external file source)
    - INI files: Simple key-value configuration (legacy system source) 
    - Environment variables: System-level configuration (OS source)
    - Default values: Hardcoded fallback configuration (application source)
    
    Data Structure Explanation:
    - Dict for config storage: Fast key-value lookups O(1) complexity
    - List for file paths: Ordered search priority for configuration files
    - Set for valid keys: Fast membership testing for configuration validation
    """
    
    def __init__(self):
        """Initialize ConfigFileManager with multiple data sources."""
        import json
        import os
        
        # Configuration data storage (primary data structure)
        self.config_data: Dict[str, Any] = {}
        
        # Valid configuration keys (data structure: set for fast lookup)
        self.valid_config_keys: set = {
            'app_name', 'debug_mode', 'max_login_attempts', 'session_timeout',
            'email_settings', 'database_settings', 'security_settings'
        }
        
        # Default configuration values (fallback data source)
        self.default_config: Dict[str, Any] = {
            'app_name': 'Golden Turf Management',
            'debug_mode': False,
            'max_login_attempts': 3,
            'session_timeout': 3600,
            'email_settings': {
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'use_tls': True
            },
            'database_settings': {
                'connection_timeout': 30,
                'max_connections': 10
            },
            'security_settings': {
                'password_min_length': 8,
                'require_special_chars': True
            }
        }
        
        # Load configuration from multiple sources
        self._load_configuration_sources()
    
    def _load_configuration_sources(self) -> None:
        """Load configuration from multiple data sources with priority order."""
        import json
        import os
        
        # Start with default configuration
        self.config_data = self.default_config.copy()
        
        # Configuration file search paths (ordered by priority)
        config_file_paths: List[str] = [
            'config.json',
            'settings.json',
            os.path.expanduser('~/.goldenturf/config.json'),
            '/etc/goldenturf/config.json'
        ]
        
        # Load JSON configuration files with while loop (iteration requirement)
        path_index = 0
        while path_index < len(config_file_paths):
            config_path = config_file_paths[path_index]
            
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as config_file:
                        json_config = json.load(config_file)
                        # Merge configuration with validation
                        self._merge_configuration(json_config, f"JSON file: {config_path}")
                        break  # Use first found configuration file
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"Warning: Could not load config from {config_path}: {e}")
            
            path_index += 1
        
        # Load environment variable overrides (additional data source)
        self._load_environment_variables()
    
    def _merge_configuration(self, new_config: Dict[str, Any], source_name: str) -> None:
        """
        Merge new configuration data with existing configuration.
        
        Args:
            new_config (Dict[str, Any]): Configuration to merge
            source_name (str): Name of configuration source for logging
            
        Data Structure Explanation:
        - Recursive dictionary merging: Preserves nested structure integrity
        - Source tracking: Maintains audit trail of configuration origins
        """
        if not isinstance(new_config, dict):
            print(f"Warning: Invalid configuration format from {source_name}")
            return
        
        # Validate configuration keys
        invalid_keys = set(new_config.keys()) - self.valid_config_keys
        if invalid_keys:
            print(f"Warning: Invalid config keys from {source_name}: {invalid_keys}")
        
        # Merge valid configuration recursively
        for key, value in new_config.items():
            if key in self.valid_config_keys:
                if isinstance(value, dict) and key in self.config_data:
                    # Recursive merge for nested dictionaries
                    if isinstance(self.config_data[key], dict):
                        self.config_data[key].update(value)
                    else:
                        self.config_data[key] = value
                else:
                    self.config_data[key] = value
    
    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables (OS data source)."""
        import os
        
        # Environment variable mapping (data structure: dictionary)
        env_var_mapping: Dict[str, str] = {
            'GOLDENTURF_APP_NAME': 'app_name',
            'GOLDENTURF_DEBUG': 'debug_mode',
            'GOLDENTURF_MAX_LOGIN_ATTEMPTS': 'max_login_attempts',
            'GOLDENTURF_SESSION_TIMEOUT': 'session_timeout'
        }
        
        # Process environment variables with iteration
        for env_var, config_key in env_var_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value:
                # Type conversion based on expected data type
                if config_key in ['debug_mode']:
                    self.config_data[config_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                elif config_key in ['max_login_attempts', 'session_timeout']:
                    try:
                        self.config_data[config_key] = int(env_value)
                    except ValueError:
                        print(f"Warning: Invalid integer value for {env_var}: {env_value}")
                else:
                    self.config_data[config_key] = env_value
    
    def get_config_value(self, config_key: str, default_value: Any = None) -> Any:
        """
        Get configuration value with fallback support.
        
        Args:
            config_key (str): Configuration key to retrieve
            default_value (Any): Fallback value if key not found
            
        Returns:
            Any: Configuration value or default
            
        Data Access Pattern:
        - Dictionary lookup: O(1) time complexity for configuration access
        - Default fallback: Ensures robust application behavior
        """
        return self.config_data.get(config_key, default_value)
    
    def get_nested_config(self, key_path: str, separator: str = '.') -> Any:
        """
        Get nested configuration value using dot notation.
        
        Args:
            key_path (str): Dot-separated path to nested value
            separator (str): Path separator character
            
        Returns:
            Any: Nested configuration value or None
            
        Example:
            get_nested_config('email_settings.smtp_port') returns 587
        """
        path_parts = key_path.split(separator)
        current_value = self.config_data
        
        # Navigate nested dictionary structure
        part_index = 0
        while part_index < len(path_parts) and isinstance(current_value, dict):
            current_key = path_parts[part_index]
            current_value = current_value.get(current_key)
            if current_value is None:
                break
            part_index += 1
        
        return current_value
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration against requirements.
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
            
        Validation Logic:
        - Type checking: Ensures configuration values have correct types
        - Range validation: Checks numeric values are within acceptable ranges
        - Existence checking: Verifies required configuration keys exist
        """
        validation_errors: List[str] = []
        
        # Required configuration validation
        required_configs = ['app_name', 'max_login_attempts', 'session_timeout']
        for required_key in required_configs:
            if required_key not in self.config_data:
                validation_errors.append(f"Missing required configuration: {required_key}")
        
        # Type and range validation
        numeric_configs = {
            'max_login_attempts': (int, 1, 10),
            'session_timeout': (int, 300, 86400)  # 5 minutes to 24 hours
        }
        
        for config_key, (expected_type, min_val, max_val) in numeric_configs.items():
            if config_key in self.config_data:
                config_value = self.config_data[config_key]
                if not isinstance(config_value, expected_type):
                    validation_errors.append(f"Invalid type for {config_key}: expected {expected_type.__name__}")
                elif not (min_val <= config_value <= max_val):
                    validation_errors.append(f"Value for {config_key} out of range: {min_val}-{max_val}")
        
        is_valid = len(validation_errors) == 0
        return is_valid, validation_errors


# Create global instances for use in route handlers (maintains existing functionality)
user_manager = UserManager()
form_processor = FormProcessor()
config_file_manager = ConfigFileManager()


def migrate_users_table() -> None:
    """
    Migrate users table to add missing columns for backward compatibility.
    
    Adds essential columns like reset_token, token_expiry, role, verification_code,
    and permissions if they don't exist. Sets the first user as admin if no
    roles are assigned.
    
    Raises:
        sqlite3.Error: If database migration fails
    """
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check current table structure
        c.execute("PRAGMA table_info(users)")
        existing_columns = [column_info[1] for column_info in c.fetchall()]

        # Add missing columns with appropriate defaults
        required_columns = {
            'reset_token': 'ALTER TABLE users ADD COLUMN reset_token TEXT',
            'token_expiry': 'ALTER TABLE users ADD COLUMN token_expiry TEXT',
            'role': 'ALTER TABLE users ADD COLUMN role TEXT DEFAULT "user"',
            'verification_code': 'ALTER TABLE users ADD COLUMN verification_code TEXT',
            'permissions': 'ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT ""'
        }

        for column_name, alter_query in required_columns.items():
            if column_name not in existing_columns:
                c.execute(alter_query)
                print(f"✓ Added {column_name} column to users table")

        # Set first user as admin if no admin exists
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        
        if admin_count == 0:
            c.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        first_user = c.fetchone()
        if first_user:
            user_id = first_user[0]
            c.execute(
                "UPDATE users SET role = ?, permissions = ? WHERE id = ?",
                ('admin', 'dashboard,payments,clients,calendar,products', user_id)
            )
            print(f"✓ Set user ID {user_id} as admin")

        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        print(f"✗ Database migration failed: {e}")
        raise



@app.route('/', methods=['GET'])
def home():
    """Root route - redirect to login page"""
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration process with validation.
    
    GET: Display registration form
    POST: Process registration data with validation
    
    Features:
        - Input validation for all fields
        - Password strength requirements
        - Email uniqueness validation
        - First user auto-admin assignment
    
    Returns:
        Rendered registration template or redirect to login
    """
    if request.method == 'POST':
        # Extract form data with mixed snake_case
        user_name = request.form.get('name', '').strip()
        user_email = request.form.get('email', '').strip()
        user_password = request.form.get('password', '').strip()

        # Input validation checks
        # Type and existence validation
        if not user_name or not user_email or not user_password:
            flash('All fields are required.')
            return render_template('register.html')

        # Range validation for password length
        MIN_PASSWORD_LENGTH = 6
        if len(user_password) < MIN_PASSWORD_LENGTH:
            flash('Password must be at least 6 characters long.')
            return render_template('register.html')

        # Email format validation
        try:
            validated_email = input_validator.validate_email(user_email, "Email")
        except ValidationError:
            flash('Please enter a valid email address.')
            return render_template('register.html')

        # Password hashing for security
        hashed_password_bytes = hashpw(user_password.encode('utf-8'), gensalt())

        # Database operations with proper connection management
        users_db_connection = sqlite3.connect('users.db')
        users_cursor = users_db_connection.cursor()
        
        try:
            # Check user count for admin assignment
            users_cursor.execute('SELECT COUNT(*) FROM users')
            total_user_count = users_cursor.fetchone()[0]
            
            # Role assignment logic
            if total_user_count == 0:
                assigned_user_role = 'admin'
                DEFAULT_ADMIN_PERMISSIONS = 'dashboard,payments,clients,calendar,products'
                user_permissions = DEFAULT_ADMIN_PERMISSIONS
                flash('Congratulations! As the first user, you have been granted admin privileges.')
            else:
                assigned_user_role = 'user'
                user_permissions = ''  # No permissions by default
                
            # Insert new user with validation
            users_cursor.execute(
                'INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)',
                (user_name, validated_email, hashed_password_bytes.decode('utf-8'), 
                 assigned_user_role, user_permissions)
            )
            users_db_connection.commit()
            flash('Registration successful!')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('Email already registered!')
        except sqlite3.Error as database_error:
            app.logger.error(f"Database error during registration: {database_error}")
            flash('Registration failed. Please try again.')
        finally:
            users_db_connection.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    """
    Handle user authentication and login process.
    
    GET: Display login form
    POST: Authenticate user credentials and establish session
    
    Returns:
        str: Rendered login template or redirect to dashboard
        
    Security Features:
        - Input validation and sanitization
        - Bcrypt password verification
        - Session management
        - Brute force protection (TODO: implement rate limiting)
        
    Note:
        Automatically creates user-specific database on successful login
    """
    # Skip redirect check for login page - always allow access
    
    if request.method == 'POST':
        try:
            # Extract and validate form data
            str_raw_email = request.form.get('email', '').strip()
            str_raw_password = request.form.get('password', '').strip()
            
            # Validate email format and requirements
            try:
                str_validated_email = input_validator.validate_email(str_raw_email, "Email")
            except ValidationError as validation_error:
                flash('Please enter a valid email address.')
                return render_template('login.html')
            
            # Validate password requirements
            try:
                str_validated_password = input_validator.validate_string(
                    str_raw_password, 
                    "Password", 
                    int_min_length=1, 
                    int_max_length=128,
                    bool_required=True
                )
            except ValidationError as validation_error:
                flash('Please enter your password.')
                return render_template('login.html')
            
            # Attempt to authenticate user
            try:
                user_data = _authenticate_user(str_validated_email, str_validated_password)
                if user_data:
                    # Set up user session
                    _create_user_session(user_data, str_validated_email)
                    
                    # Initialize user-specific database
                    _initialize_user_database(str_validated_email)
                    
                    flash('Welcome back!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid email or password.')
                    
            except Exception as db_error:
                app.logger.error(f"Database error during login: {db_error}")
                flash('An error occurred during login. Please try again.')
                
        except Exception as general_error:
            app.logger.error(f"Unexpected error in login: {general_error}")
            flash('An unexpected error occurred. Please try again.')
    
    return render_template('login.html')


def _authenticate_user(str_email: str, str_password: str) -> Optional[Tuple]:
    """
    Authenticate user credentials against the database.
    
    Args:
        str_email (str): Validated email address
        str_password (str): User-provided password
        
    Returns:
        Optional[Tuple]: User data tuple if authentication successful, None otherwise
        
    Security:
        - Uses bcrypt for password verification
        - Falls back to plain text for legacy passwords
        - Sanitizes database queries with parameters
    """
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            'SELECT id, name, role, password, permissions FROM users WHERE email = ?', 
            (str_email,)
        )
        user_data = c.fetchone()
        
        if not user_data:
            conn.close()
            return None
        
        int_user_id, str_user_name, str_user_role, str_stored_password, str_user_permissions = user_data
        
        # Verify password using appropriate method
        if _is_bcrypt_hash(str_stored_password):
            # Use bcrypt verification for hashed passwords
            if security_manager.verify_password(str_password, str_stored_password):
                conn.close()
                return user_data
        else:
            # Legacy plain text comparison (should be migrated)
            app.logger.warning(f"User {str_email} using legacy plain text password")
            if str_password == str_stored_password:
                # TODO: Automatically hash the password for future use
                conn.close()
                return user_data
        
        conn.close()
                
    except sqlite3.Error as db_error:
        app.logger.error(f"Database error in _authenticate_user: {db_error}")
        
    return None


def _is_bcrypt_hash(str_password: str) -> bool:
    """
    Check if password string is a bcrypt hash.
    
    Args:
        str_password (str): Password string to check
        
    Returns:
        bool: True if string appears to be bcrypt hash
    """
    return (
        isinstance(str_password, str) and 
        (str_password.startswith('$2b$') or str_password.startswith('$2a$'))
    )


def _create_user_session(user_data: Tuple, str_email: str) -> None:
    """
    Create and configure user session data.
    
    Args:
        user_data (Tuple): Database user record
        str_email (str): User's email address
        
    Note:
        Sets session variables for user identification and permissions
    """
    int_user_id, str_user_name, str_user_role, _, str_user_permissions = user_data
    
    session['user_id'] = int_user_id
    session['user_name'] = str_user_name
    session['user_role'] = str_user_role if str_user_role else 'user'
    session['user_permissions'] = str_user_permissions if str_user_permissions else ''
    session['database'] = f'{str_email}_db.sqlite'
    
    # Log successful authentication (without sensitive data)
    app.logger.info(f"User authenticated: ID={int_user_id}, Role={str_user_role}")


def _initialize_user_database(str_email: str) -> None:
    """
    Initialize user-specific database with required tables.
    
    Args:
        str_email (str): User's email for database naming
        
    Note:
        Creates database if it doesn't exist and sets up required schema
    """
    try:
        str_database_name = f'{str_email}_db.sqlite'
        user_db = sqlite3.connect(str_database_name)
        
        # Create clients table if not exists
        user_db.execute('''CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            account_type TEXT DEFAULT 'Active',
            company_name TEXT,
            actions TEXT,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP,
            owner_id INTEGER,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )''')
        
        # Create invoices table if not exists
        user_db.execute('''CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            product TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            price DECIMAL(10,2) NOT NULL,
            gst DECIMAL(10,2) DEFAULT 0,
            total DECIMAL(10,2) NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            extras_json TEXT,
            owner_id INTEGER,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )''')
        
        # Create tasks table if not exists
        user_db.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            task_date DATE NOT NULL,
            task_time TIME,
            task_end_time TIME,
            location TEXT,
            status TEXT DEFAULT 'Not completed',
            assigned_user_id INTEGER,
            owner_id INTEGER,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_user_id) REFERENCES users(id),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )''')
        
        user_db.commit()
        user_db.close()
        
        app.logger.info(f"User database initialized: {str_database_name}")
        
    except sqlite3.Error as db_error:
        app.logger.error(f"Failed to initialize user database: {db_error}")
        # Don't fail login for database initialization errors
        pass

@app.route('/dashboard')
def dashboard():
    """
    Display main dashboard with business metrics and data.
    
    Features:
        - User session validation
        - Permission-based access control
        - Business metrics calculation (sales, clients, jobs)
        - Time-based analytics (today, yesterday, week)
    
    Returns:
        Rendered dashboard template with business data
        
    Validation:
        - Session existence check
        - Permission authorization
        - User ID validation
    """
    # Session validation
    if 'user_name' not in session:
        app.logger.debug("Dashboard access denied: No user_name in session")
        return redirect(url_for('login'))

    # Permission validation
    if not has_permission('dashboard'):
        return redirect(url_for('access_restricted'))

    # User ID validation
    int_user_id = session.get('user_id')
    if not int_user_id:
        return redirect(url_for('login'))

    app.logger.debug(f"Dashboard accessed: user_name={session.get('user_name')}, user_role={session.get('user_role')}")

    # Get user role for data access control
    current_user_role = session.get('user_role', 'user')
    
    # Database connection for metrics retrieval
    users_database_connection = sqlite3.connect('users.db')
    metrics_cursor = users_database_connection.cursor()
    
    # Get all clients data
    metrics_cursor.execute('SELECT * FROM clients')
    all_clients_list = metrics_cursor.fetchall()
    
    # Get all jobs data
    metrics_cursor.execute('SELECT * FROM jobs')
    all_jobs_list = metrics_cursor.fetchall()
    
    # Get all invoices/payments with client details
    metrics_cursor.execute('''
        SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date, 
               invoices.product, invoices.quantity, invoices.price, invoices.gst, 
               invoices.total, invoices.owner_id
        FROM invoices
        LEFT JOIN clients ON invoices.client_id = clients.id
        ORDER BY invoices.created_date DESC
    ''')
    all_payments_list = metrics_cursor.fetchall()
    
    users_database_connection.close()

    # Date calculations for analytics
    today_date = datetime.now().date()
    yesterday_date = today_date - timedelta(days=1)
    DAYS_IN_WEEK = 7
    last_week_date = today_date - timedelta(days=DAYS_IN_WEEK)

    # Calculate total clients
    total_clients_count = len(all_clients_list)

    # Filter paid invoices for sales calculations
    paid_invoices_list = [payment_tuple for payment_tuple in all_payments_list if payment_tuple[2] != 'Unpaid']
    
    # Calculate total sales (all invoices for comparison)
    total_all_invoices_amount = sum(float(payment_tuple[8]) for payment_tuple in all_payments_list if payment_tuple[8] is not None)
    
    # Calculate sales from paid invoices only
    total_paid_sales_amount = sum(float(payment_tuple[8]) for payment_tuple in paid_invoices_list if payment_tuple[8] is not None)
    
    # Time-based sales calculation
    today_sales_amount = 0.0
    yesterday_sales_amount = 0.0
    weekly_sales_amount = 0.0
    
    for tuple_payment in list_paid_payments:
        if tuple_payment[8] is not None and tuple_payment[3]:  # Has total and date
            try:
                # Date parsing and validation
                date_invoice = datetime.strptime(tuple_payment[3], '%Y-%m-%d %H:%M:%S').date()
                float_amount = float(tuple_payment[8])
                
                # Daily sales calculation
                if date_invoice == date_today:
                    float_today_sales += float_amount
                elif date_invoice == date_yesterday:
                    float_yesterday_sales += float_amount
                    
                # Weekly sales calculation
                if date_invoice >= date_last_7_days:
                    float_week_sales += float_amount
                    
            except (ValueError, TypeError) as date_error:
                app.logger.error(f"Date parsing error for payment {tuple_payment[0]}: {date_error}")
                continue
    
    # Debug logging for calculations
    app.logger.debug(f"Dashboard calculations for user {session.get('user_name')} (role: {str_user_role}):")
    app.logger.debug(f"  Total invoices: {len(list_all_payments)}")
    app.logger.debug(f"  Paid invoices: {len(list_paid_payments)}")
    app.logger.debug(f"  Total sales (all): ${float_total_all_invoices}")
    app.logger.debug(f"  Total sales (paid): ${float_total_sales_paid}")
    app.logger.debug(f"  Daily sales: Today=${float_today_sales}, Yesterday=${float_yesterday_sales}")
    app.logger.debug(f"  Weekly sales: ${float_week_sales}")

    # Job analytics calculation
    list_upcoming_jobs = [tuple_job for tuple_job in list_all_jobs 
                         if datetime.strptime(tuple_job[2], '%Y-%m-%d').date() >= date_today]
    list_overdue_jobs = [tuple_job for tuple_job in list_all_jobs 
                        if datetime.strptime(tuple_job[2], '%Y-%m-%d').date() < date_today and tuple_job[3] != 'Completed']

    # Task data retrieval
    conn_users_db = sqlite3.connect('users.db')
    c = conn.cursor()
    overdue_jobs_info = []
    for job in overdue_jobs:
        c.execute('SELECT client_name FROM clients WHERE id = ?', (job[1],))  # Removed owner_id restriction
        client_name = c.fetchone()
        if client_name:
            overdue_jobs_info.append({'client_name': client_name[0], 'job_date': job[2]})
    conn.close()

    # Fetch admin users
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT name, email FROM users WHERE role = 'admin'")
    admins = c.fetchall()
    conn.close()

    return render_template('dashboard_updated.html',
                           total_clients=total_clients,
                           total_sales=total_sales_paid_only,  # Show only paid invoices
                           total_all_sales=total_all_invoices,  # Include all invoices total for debugging
                           today_sales=today_sales,
                           yesterday_sales=yesterday_sales,
                           last_7_days_sales=last_7_days_sales,
                           overdue_jobs=overdue_jobs_info,
                           user_role=user_role,
                           admins=admins)

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

def query_all_clients(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM clients')  # Removed owner_id restriction - all users see all clients
    clients = c.fetchall()
    conn.close()
    return clients

def query_all_jobs(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM jobs WHERE owner_id = ?', (user_id,))
    jobs = c.fetchall()
    conn.close()
    return jobs

def query_all_payments(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Updated query to ensure we get owner_id and all invoice data properly
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date, 
                        invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.owner_id
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  WHERE invoices.owner_id = ?
                  ORDER BY invoices.created_date DESC''', (user_id,))
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
        task_end_time TEXT,
        location TEXT,
        status TEXT NOT NULL DEFAULT 'Not completed',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    conn.close()

def migrate_clients_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(clients)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE clients ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing clients (assuming first user is admin)
        c.execute("UPDATE clients SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_invoices_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(invoices)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE invoices ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing invoices
        c.execute("UPDATE invoices SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_tasks_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(tasks)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE tasks ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing tasks
        c.execute("UPDATE tasks SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_quotes_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(quotes)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE quotes ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing quotes
        c.execute("UPDATE quotes SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

def migrate_jobs_owner_id():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(jobs)")
    columns = [info[1] for info in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE jobs ADD COLUMN owner_id INTEGER")
        # Set owner_id to 1 for existing jobs
        c.execute("UPDATE jobs SET owner_id = 1 WHERE owner_id IS NULL")
        conn.commit()
    conn.close()

migrate_clients_table()
create_tasks_table()
migrate_tasks_table()
migrate_users_table()
migrate_clients_owner_id()
migrate_invoices_owner_id()
migrate_tasks_owner_id()
migrate_quotes_owner_id()
migrate_jobs_owner_id()

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    """
    Client management interface with CRUD operations.
    Handles client creation, listing, and validation with shared access.
    """
    # Session validation
    if 'user_name' not in session:
        return redirect(url_for('login'))

    # Permission validation
    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
        
    # User ID validation
    current_user_id = session.get('user_id')
    if not current_user_id:
        return redirect(url_for('login'))

    # Initialize response variables
    error_message = None
    success_message = None

    # Database connection
    clients_database_connection = sqlite3.connect('users.db')
    clients_cursor = clients_database_connection.cursor()

    if request.method == 'POST':
        # Extract form data with mixed snake_case
        contact_name = request.form.get('contact_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        account_type = request.form.get('account_type', '').strip()
        company_name = request.form.get('company_name', '').strip()
        client_email = request.form.get('email', '').strip()
        client_actions = request.form.get('actions', '').strip()
        DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        created_date = datetime.now().strftime(DATETIME_FORMAT)

        # Input validation checks
        import re
        VALID_ACCOUNT_TYPES = ['Active', 'Deactivated']
        NAME_PATTERN = r'^[A-Za-z ]+$'
        
        if not re.match(NAME_PATTERN, contact_name):
            error_message = 'Contact name is required and must contain only alphabetic characters and spaces.'
        elif phone_number and (not phone_number.isdigit()):
            error_message = 'Phone number must contain digits only if provided.'
        elif account_type not in VALID_ACCOUNT_TYPES:
            error_message = 'Invalid account type selected.'
        elif '@' not in client_email or '.' not in client_email:
            error_message = 'Invalid email format.'

        # Save client if validation passes
        if not error_message:
            clients_cursor.execute('''INSERT INTO clients (client_name, email, phone, account_type, company_name, actions, created_date, owner_id)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                          (contact_name, client_email, phone_number, account_type, 
                           company_name, client_actions, created_date, current_user_id))
            clients_database_connection.commit()
            success_message = 'Client saved successfully.'

    # Get all clients (shared access for all users)
    clients_cursor.execute('SELECT * FROM clients')
    all_clients_list = clients_cursor.fetchall()
    print(f"DEBUG: User {current_user_id} can see {len(all_clients_list)} clients (all shared)")
    clients_database_connection.close()

    return render_template('clients.html', 
                         clients=all_clients_list, 
                         error=error_message, 
                         success=success_message)

@app.route('/logout')
def logout():
    """
    User logout function - clears session and redirects to login.
    Simple session cleanup for user authentication.
    """
    session.pop('user_name', None)
    return redirect(url_for('login'))

@app.route('/access_restricted')
def access_restricted():
    """
    Access restriction page for unauthorized users.
    Shows restricted access message with special admin override.
    """
    # Session validation
    if 'user_name' not in session:
        return redirect(url_for('login'))
        
    # Admin override - user ID 1 always has access
    int_session_user_id = session.get('user_id')
    if int_session_user_id == 1:
        return redirect(url_for('dashboard'))
        
    return render_template('access_restricted.html')

@app.route('/profiles', methods=['GET', 'POST'])
def profiles():
    """
    User profile management interface for admin users.
    Handles user creation, editing, and role management.
    """
    # Session validation
    if 'user_name' not in session:
        return redirect(url_for('login'))

    # Permission validation
    if not has_permission('profiles'):
        return redirect(url_for('access_restricted'))

    if request.method == 'POST':
        # Extract form data with Hungarian notation
        str_profile_name = request.form['name']
        str_profile_email = request.form['email']
        password = request.form['password']

        if not name or not email or not password:
            flash('All fields are required.')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long.')
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            permissions = ''  # No permissions by default for new users
            try:
                c.execute('INSERT INTO users (name, email, password, role, permissions) VALUES (?, ?, ?, ?, ?)', (name, email, password, 'user', permissions))
                conn.commit()
                flash('User added successfully!')
            except sqlite3.IntegrityError:
                flash('Email already exists!')
            conn.close()

        return redirect(url_for('profiles'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Do not forcibly set user ID 1 as admin; allow demotion if at least one admin remains
    c.execute('SELECT id, name, email, role, permissions FROM users ORDER BY id')
    users = c.fetchall()
    # Find all admin users
    c.execute('SELECT id FROM users WHERE role = "admin"')
    admin_ids = [row[0] for row in c.fetchall()]
    conn.close()
    # If only one admin, pass that admin's id for disabling
    only_admin_id = admin_ids[0] if len(admin_ids) == 1 else None
    return render_template('profiles.html', users=users, only_admin_id=only_admin_id)

@app.route('/profiles/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Check if the user being deleted is the current user
    is_self_delete = user_id == session.get('user_id')
    # Delete the user
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()

    # Reorder IDs sequentially
    c.execute('SELECT id FROM users ORDER BY id')
    users = c.fetchall()
    for index, user in enumerate(users, start=1):
        c.execute('UPDATE users SET id = ? WHERE id = ?', (index, user[0]))
    conn.commit()

    # Reset the sqlite_sequence to ensure next insert uses sequential ID
    c.execute("UPDATE sqlite_sequence SET seq = (SELECT MAX(id) FROM users) WHERE name='users'")
    conn.commit()

    # After deletion, check if any admins remain
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = c.fetchone()[0]
    if admin_count == 0:
        # Promote user ID 1 to admin if exists
        c.execute('SELECT id FROM users WHERE id = 1')
        user1 = c.fetchone()
        if user1:
            c.execute('UPDATE users SET role = "admin" WHERE id = 1')
            conn.commit()

    conn.close()

    if is_self_delete:
        session.clear()
        flash('Your account was deleted. If no admins remained, user ID 1 is now admin.')
        return redirect(url_for('login'))

    flash('User deleted successfully!')
    return redirect(url_for('profiles'))

@app.route('/profiles/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Check if there is only one admin in the system (after connection)
    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    only_one_admin = c.fetchone()[0] == 1
    session['only_one_admin'] = only_one_admin

    c.execute('SELECT id, name, email, role, permissions FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        # Role and permissions may be disabled for self-edit, so get from DB if not in form
        role = request.form.get('role') or (user[3] if user else 'user')
        permissions = ','.join(request.form.getlist('permissions')) if request.form.getlist('permissions') else (user[4] if user else '')

        current_user_id = session.get('user_id')

        # Prevent demoting user ID 1 or the only admin
        is_id1 = user_id == 1
        only_one_admin = (user and user[3] == 'admin' and session.get('only_one_admin'))
        if (is_id1 or only_one_admin) and role != 'admin':
            flash('User ID 1 and the only admin must always remain admin.')
        elif not name or not email:
            flash('Name and email are required.')
        elif len(password) < 6 and password:
            flash('Password must be at least 6 characters long if provided.')
        else:
            if password:
                c.execute('UPDATE users SET name = ?, email = ?, password = ?, role = ?, permissions = ? WHERE id = ?',
                          (name, email, password, role, permissions, user_id))
            else:
                c.execute('UPDATE users SET name = ?, email = ?, role = ?, permissions = ? WHERE id = ?',
                          (name, email, role, permissions, user_id))
            conn.commit()
            flash('User updated successfully!')
            conn.close()
            return redirect(url_for('profiles'))

    conn.close()

    if not user:
        flash('User not found.')
        return redirect(url_for('profiles'))

    # For admins, always show all permissions as checked and disabled
    is_admin = user and user[3] == 'admin'
    all_permissions = ['dashboard', 'clients', 'products_list', 'quotes', 'payments', 'calendar', 'profiles']
    user_permissions = user[4].split(',') if user and user[4] else []
    return render_template('edit_user.html', user=user, is_admin=is_admin, all_permissions=all_permissions, user_permissions=user_permissions)

@app.route('/profiles/toggle_admin/<int:user_id>', methods=['POST'])
def toggle_admin(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    current_user_id = session.get('user_id')

    if not can_change_role(current_user_id, user_id):
        flash('You cannot change your own role.')
        return redirect(url_for('profiles'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    current_role = c.fetchone()[0]
    new_role = 'user' if current_role == 'admin' else 'admin'

    if not can_demote_admin(user_id, new_role):
        # Check admin count for error message
        conn2 = sqlite3.connect('users.db')
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c2.fetchone()[0]
        conn2.close()
        if admin_count == 1:
            flash('Cannot remove admin rights if only one admin remains.')
        else:
            flash('Cannot remove admin rights.')
        conn.close()
        return redirect(url_for('profiles'))

    c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()

    # If the current user is revoking their own admin, update session and redirect
    if user_id == current_user_id and new_role == 'user':
        session['user_role'] = 'user'
        flash('You have revoked your own admin rights. Access is now restricted.')
        return redirect(url_for('access_restricted'))

    flash(f'User role updated to {new_role}!')
    return redirect(url_for('profiles'))

@app.route('/profiles/update_permissions/<int:user_id>', methods=['POST'])
def update_permissions(user_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    # Get list of permissions from checkboxes
    permissions_list = request.form.getlist('permissions')
    permissions = ','.join(permissions_list)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET permissions = ? WHERE id = ?', (permissions, user_id))
    conn.commit()
    conn.close()

    # If the current user's permissions were updated, update session immediately
    if user_id == session.get('user_id'):
        session['user_permissions'] = permissions

    flash('User permissions updated!')
    return redirect(url_for('profiles'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = ''
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            message = 'Please enter your email address.'
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = c.fetchone()
            if user:
                # Generate 6-digit verification code
                verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
                token_expiry = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
                c.execute('UPDATE users SET verification_code = ?, token_expiry = ? WHERE email = ?', (verification_code, token_expiry, email))
                conn.commit()

                # Send email with verification code
                msg = Message('Your Verification Code', sender='noreply@goldenturf.com', recipients=[email])
                msg.body = f'Your verification code is: {verification_code}'
                mail.send(msg)  # Uncommented to enable email sending

                conn.close()
                return redirect(url_for('verify_code', email=email))
            else:
                message = 'If this email is registered, a verification code has been sent.'
            conn.close()
    return render_template('forgotpassword.html', message=message)

@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    message = ''
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not new_password or not confirm_password:
            message = 'Please fill in all fields.'
        elif len(new_password) < 6:
            message = 'Password must be at least 6 characters long.'
        elif new_password != confirm_password:
            message = 'Passwords do not match.'
        else:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ? AND token_expiry > ?', (email, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            user = c.fetchone()
            if user:
                c.execute('UPDATE users SET password = ?, verification_code = NULL, token_expiry = NULL WHERE id = ?', (new_password, user[0]))
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            else:
                message = 'Invalid or expired reset token.'
                conn.close()

    return render_template('reset_password.html', message=message, email=email)

@app.route('/invoice', methods=['GET', 'POST'])
def invoice():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('invoice'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    # Fetch all product prices from DB for dynamic pricing
    c.execute('SELECT product_name, price FROM products')
    price_table = {}
    for row in c.fetchall():
        try:
            price_table[row[0]] = float(row[1]) if row[1] else 0.0
        except (ValueError, TypeError):
            # Handle non-numeric prices like "Custom"
            price_table[row[0]] = 0.0


    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        turf_type = request.form.get('turf_type', '').strip()
        area_val = request.form.get('area', type=float)
        payment_status = request.form.get('payment_status', '').strip()
        gst = request.form.get('gst') == 'yes'

        # Calculate base price
        base_price = price_table.get(turf_type, 0) * area_val if area_val else 0

        # Calculate extras cost
        extras_cost = 0
        extras_details = []

        # Artificial Hedges
        hedges_qty = request.form.get('artificial_hedges_qty', type=int)
        if hedges_qty and hedges_qty > 0:
            extras_cost += 60 * hedges_qty
            extras_details.append(f"Artificial Hedges: {hedges_qty}")

        # Fountain
        fountain_price = request.form.get('fountain_price', type=float)
        db_fountain_price = price_table.get('Fountains', 0)
        if fountain_price and fountain_price > 0:
            extras_cost += fountain_price
            extras_details.append(f"Fountain: ${fountain_price}")
        elif db_fountain_price:
            extras_cost += db_fountain_price
            extras_details.append(f"Fountain: ${db_fountain_price}")

        # Bamboo Products
        bamboo_size = request.form.get('bamboo_products_size')
        bamboo_qty = request.form.get('bamboo_products_qty', type=int)
        if bamboo_size and bamboo_qty and bamboo_qty > 0:
            bamboo_key = f"Bamboo ({bamboo_size})" if bamboo_size in ['2m', '2.4m', '1.8m'] else None
            bamboo_price = price_table.get(bamboo_key, 0)
            extras_cost += bamboo_price * bamboo_qty
            extras_details.append(f"Bamboo {bamboo_size}: {bamboo_qty}")

        # Pebbles (merged, custom type)
        pebbles_custom_type = request.form.get('pebbles_custom_type')
        pebbles_qty = request.form.get('pebbles_qty', type=int)
        if pebbles_custom_type and pebbles_qty and pebbles_qty > 0:
            if pebbles_custom_type.lower() in ['multicolour', 'glow']:
                pebbles_price = price_table.get('Pebbles Multicolour/Glow', 0)
            else:
                pebbles_price = price_table.get('Pebbles Standard', 0)
            extras_cost += pebbles_price * pebbles_qty
            extras_details.append(f"Pebbles ({pebbles_custom_type}): {pebbles_qty}")

        # Pegs
        pegs_qty = request.form.get('pegs_qty', type=int)
        if pegs_qty and pegs_qty > 0:
            extras_cost += 25 * pegs_qty
            extras_details.append(f"Pegs: {pegs_qty}")

        # Adhesive Tape
        tape_qty = request.form.get('adhesive_tape_qty', type=int)
        if tape_qty and tape_qty > 0:
            extras_cost += 25 * tape_qty
            extras_details.append(f"Adhesive Tape: {tape_qty}")

        # Total price calculation
        price = base_price + extras_cost
        gst_amount = price * 0.10 if gst else 0
        total_price = price + gst_amount

        # Get client_id from client_name and validate
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client_row = c.fetchone()
        if not client_row:
            # Client not found, show error and do not save invoice
            c.execute('SELECT client_name FROM clients')
            clients = [row[0] for row in c.fetchall()]
            c.execute('SELECT product_name FROM products')
            products = [row[0] for row in c.fetchall()]
            conn.close()
            error = f"Client '{client_name}' not found. Please select a client from the list."
            return render_template('invoice.html', error=error, clients=clients, products=products, client_name=client_name, turf_type=turf_type, area=area_val, payment_status=payment_status, gst='yes' if gst else '', summary=None)

        client_id = client_row[0]
        import json
        extras_json = json.dumps(extras_details)

        # Save invoice to database with sequential ID
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"DEBUG: Creating invoice with date: {current_date}")
        
        # Find the next available sequential ID starting from 1 - GLOBAL for all users
        c.execute('SELECT id FROM invoices ORDER BY id')
        existing_ids = [row[0] for row in c.fetchall()]
        
        # Find the first gap or next number
        next_id = 1
        for existing_id in existing_ids:
            if existing_id == next_id:
                next_id += 1
            else:
                break
        
        print(f"DEBUG: Assigning global invoice ID: {next_id}")
        
        c.execute('''INSERT INTO invoices (id, client_id, product, quantity, price, gst, total, status, created_date, extras_json, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (next_id, client_id, turf_type, area_val, price, gst_amount, total_price, payment_status, current_date, extras_json, session['user_id']))
        conn.commit()

        # Fetch updated invoices - ALL INVOICES
        c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
                      invoices.gst, invoices.total, invoices.status, invoices.created_date
                      FROM invoices
                      LEFT JOIN clients ON invoices.client_id = clients.id
                      ORDER BY invoices.id ASC''')
        invoices = c.fetchall()
        conn.close()

        return render_template('invoice.html', invoices=invoices, summary={
            'client_name': client_name,
            'turf_type': turf_type,
            'area': area_val,
            'extras_cost': extras_cost,
            'gst': gst_amount,
            'total_price': total_price
        })

    # For GET request, fetch ALL invoices
    c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price,
                  invoices.gst, invoices.total, invoices.status, invoices.created_date
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  ORDER BY invoices.id ASC''')
    invoices = c.fetchall()
    
    conn.close()
    return render_template('invoice.html', clients=clients, products=products, price_table=price_table, invoices=invoices)

@app.route('/products_list', methods=['GET', 'POST'])
def products_list():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('products_list'):
        return redirect(url_for('access_restricted'))
    import json
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Handle grouped/edited price and stock updates
    if request.method == 'POST':
        # Bamboo products
        bamboo_2m_stock = request.form.get('bamboo_2m_stock', type=int)
        bamboo_2m_price = request.form.get('bamboo_2m_price', type=float)
        bamboo_24m_stock = request.form.get('bamboo_24m_stock', type=int)
        bamboo_24m_price = request.form.get('bamboo_24m_price', type=float)
        bamboo_18m_stock = request.form.get('bamboo_18m_stock', type=int)
        bamboo_18m_price = request.form.get('bamboo_18m_price', type=float)
        
        # Pebbles
        pebbles_black_stock = request.form.get('pebbles_black_stock', type=int)
        pebbles_black_price = request.form.get('pebbles_black_price', type=float)
        pebbles_white_stock = request.form.get('pebbles_white_stock', type=int)
        pebbles_white_price = request.form.get('pebbles_white_price', type=float)
        
        # Fountain
        fountain_stock = request.form.get('fountain_stock', type=int)
        fountain_price = request.form.get('fountain_price')  # custom, can be text
        
        # Turf products
        premium_stock = request.form.get('premium_stock', type=int)
        premium_price = request.form.get('premium_price', type=float)
        green_lush_stock = request.form.get('green_lush_stock', type=int)
        green_lush_price = request.form.get('green_lush_price', type=float)
        natural_40mm_stock = request.form.get('natural_40mm_stock', type=int)
        natural_40mm_price = request.form.get('natural_40mm_price', type=float)
        golf_turf_stock = request.form.get('golf_turf_stock', type=int)
        golf_turf_price = request.form.get('golf_turf_price', type=float)
        imperial_lush_stock = request.form.get('imperial_lush_stock', type=int)
        imperial_lush_price = request.form.get('imperial_lush_price', type=float)
        
        # Other products
        pegs_stock = request.form.get('pegs_stock', type=int)
        pegs_price = request.form.get('pegs_price', type=float)
        artificial_hedges_stock = request.form.get('artificial_hedges_stock', type=int)
        artificial_hedges_price = request.form.get('artificial_hedges_price', type=float)
        adhesive_tape_stock = request.form.get('adhesive_tape_stock', type=int)
        adhesive_tape_price = request.form.get('adhesive_tape_price', type=float)

        # Update DB for each product
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_2m_stock, bamboo_2m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_24m_stock, bamboo_24m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (bamboo_18m_stock, bamboo_18m_price, 'Bamboo Products'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pebbles_black_stock, pebbles_black_price, 'Black Pebbles'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pebbles_white_stock, pebbles_white_price, 'White Pebbles'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (fountain_stock, fountain_price, 'Fountains'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (premium_stock, premium_price, 'Golden Premium Turf'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (green_lush_stock, green_lush_price, 'Golden Green Lush'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (natural_40mm_stock, natural_40mm_price, 'Golden Natural 40mm'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (golf_turf_stock, golf_turf_price, 'Golden Golf Turf'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (imperial_lush_stock, imperial_lush_price, 'Golden Imperial Lush'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (pegs_stock, pegs_price, 'Peg (U-pins/Nails)'))
        c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (artificial_hedges_stock, artificial_hedges_price, 'Artificial Hedges'))
        # Note: Adhesive Tape doesn't exist in DB, we'll need to add it or skip it
        try:
            c.execute('UPDATE products SET stock=?, price=? WHERE product_name=?', (adhesive_tape_stock, adhesive_tape_price, 'Adhesive Tape'))
        except:
            pass  # Skip if product doesn't exist
        
        conn.commit()
        # Add success message
        flash('Product prices and stock updated successfully!', 'success')
        # Redirect to avoid resubmission on page refresh
        return redirect(url_for('products_list'))

    c.execute('SELECT product_name, turf_type, description, stock, price, image_url, image_urls FROM products')
    rows = c.fetchall()
    conn.close()

    # Extract specific product values for template variables
    bamboo_products = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_2m_stock = bamboo_products[3] if bamboo_products else 0
    bamboo_2m_price = bamboo_products[4] if bamboo_products else 40.00

    bamboo_24m = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_24m_stock = bamboo_24m[3] if bamboo_24m else 0
    bamboo_24m_price = bamboo_24m[4] if bamboo_24m else 38.00

    bamboo_18m = next((row for row in rows if row[0] == 'Bamboo Products'), None)
    bamboo_18m_stock = bamboo_18m[3] if bamboo_18m else 0
    bamboo_18m_price = bamboo_18m[4] if bamboo_18m else 38.00

    pebbles_black = next((row for row in rows if row[0] == 'Black Pebbles'), None)
    pebbles_black_stock = pebbles_black[3] if pebbles_black else 0
    pebbles_black_price = pebbles_black[4] if pebbles_black else 18.00

    pebbles_white = next((row for row in rows if row[0] == 'White Pebbles'), None)
    pebbles_white_stock = pebbles_white[3] if pebbles_white else 0
    pebbles_white_price = pebbles_white[4] if pebbles_white else 15.00

    fountain = next((row for row in rows if row[0] == 'Fountains'), None)
    fountain_stock = fountain[3] if fountain else 0
    fountain_price = fountain[4] if fountain else 'Custom'

    # Add missing product variables
    premium = next((row for row in rows if row[0] == 'Golden Premium Turf'), None)
    premium_stock = premium[3] if premium else 50
    premium_price = premium[4] if premium else 45.00

    green_lush = next((row for row in rows if row[0] == 'Golden Green Lush'), None)
    green_lush_stock = green_lush[3] if green_lush else 50
    green_lush_price = green_lush[4] if green_lush else 42.00

    natural_40mm = next((row for row in rows if row[0] == 'Golden Natural 40mm'), None)
    natural_40mm_stock = natural_40mm[3] if natural_40mm else 50
    natural_40mm_price = natural_40mm[4] if natural_40mm else 40.00

    golf_turf = next((row for row in rows if row[0] == 'Golden Golf Turf'), None)
    golf_turf_stock = golf_turf[3] if golf_turf else 30
    golf_turf_price = golf_turf[4] if golf_turf else 55.00

    imperial_lush = next((row for row in rows if row[0] == 'Golden Imperial Lush'), None)
    imperial_lush_stock = imperial_lush[3] if imperial_lush else 40
    imperial_lush_price = imperial_lush[4] if imperial_lush else 48.00

    pegs = next((row for row in rows if row[0] == 'Peg (U-pins/Nails)'), None)
    pegs_stock = pegs[3] if pegs else 200
    pegs_price = pegs[4] if pegs else 20.00

    artificial_hedges = next((row for row in rows if row[0] == 'Artificial Hedges'), None)
    artificial_hedges_stock = artificial_hedges[3] if artificial_hedges else 25
    artificial_hedges_price = artificial_hedges[4] if artificial_hedges else 60.00

    # Adhesive Tape doesn't exist in DB, use defaults
    adhesive_tape_stock = 50
    adhesive_tape_price = 25.00

    # Restore all product image lists
    imperial_lush_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/07/Description-premium-photo-.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/PREMIUM_15-1536x1152.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/FB_IMG_1596714611957.jpg'
    ]
    green_lush_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/04/lush-green.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush5.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Lush4.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/lush6-1.jpg'
    ]
    natural_40mm_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/natural.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Natural_4.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Natural_1-1152x1536.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/IMG-20191221-WA0026.jpg'
    ]
    golf_turf_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/home_golf_court_golf_carpet-8.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/selected-golf_carpet_golf_putting_green-11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-2-1536x864.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-6.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/golf_carpet_golf_putting_green-9-1536x864.jpg'
    ]
    premium_turf_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/premium.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/Description-premium-photo-.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/Premium_13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/06/PREMIUM_15-1536x1152.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/FB_IMG_1596714611957.jpg'
    ]
    artificial_hedges_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/07/1-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155406.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155305.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/image7.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155421.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-04-at-3.42.28-AM.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-10-at-4.09.19-PM-1152x1536.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-10-at-4.09.18-PM-1152x1536.jpeg'
    ]
    fountain_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/fountain1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210305-WA0041.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0043.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG_20210805_155305.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/07/p-fountain-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0041.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/fountain-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0031.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210205-WA0032.jpg'
    ]
    bamboo_images = [
        'https://goldenturf.com.au/wp-content/uploads/2021/06/bamboo13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/bamboo555.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/bamboo-wall1-1536x1024.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2020/06/131962086_2195562777243324_1164272107425441220_n.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/6.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/received_521798048828349-1152x1536.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20191120-WA0034.jpg'
    ]
    peg_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/peg2.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/7130I8TfLkL._SL1000_.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/DIY2-768x1024-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/Is-Artificial-Grass-Toxic-QA2-802551536.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/maxresdefault.jpg'
    ]
    tape_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/a-tape2.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/IMG-20210228-WA0034.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/7130I8TfLkL._SL1000_.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/Tape.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/maxresdefault.jpg'
    ]
    pebbles_images = [
        'https://goldenturf.com.au/wp-content/uploads/2020/06/glowing-pebble1-1.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/pebbles600x600.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/8.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/9.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/11.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/12.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/02/13.jpg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/received_410804926973400-e1628237434738.jpeg',
        'https://goldenturf.com.au/wp-content/uploads/2021/08/WhatsApp-Image-2021-08-04-at-18.35.25.jpeg'
    ]

    products = []
    pebbles = None
    for row in rows:
        image_urls = []
        if row[6]:
            try:
                image_urls = json.loads(row[6])
            except Exception:
                image_urls = []
        if not image_urls and row[5]:
            image_urls = [row[5]]

        # Main turf products
        if row[0] == 'Golden Imperial Lush':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': imperial_lush_images
            })
        elif row[0] == 'Golden Green Lush':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': green_lush_images
            })
        elif row[0] == 'Golden Natural 40mm':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': natural_40mm_images
            })
        elif row[0] == 'Golden Golf Turf':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': golf_turf_images
            })
        elif row[0] == 'Golden Premium Turf':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': premium_turf_images
            })
        # Accessories/extras: always use correct multi-image list
        elif row[0] == 'Artificial Hedges':
            products.append({
                'product_name': 'Artificial Hedges (per 50cm x 50cm)',
                'turf_type': '',
                'description': 'Artificial Hedges',
                'stock': row[3],
                'price': 10.0,
                'image_urls': artificial_hedges_images
            })
        elif row[0] == 'Fountain':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': 0,
                'image_urls': fountain_images
            })
        elif row[0] == 'Bamboo':
            # Add all bamboo sizes as separate products
            products.append({
                'product_name': 'Bamboo (2m)',
                'turf_type': '',
                'description': 'Bamboo 2 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
            products.append({
                'product_name': 'Bamboo (2.4m)',
                'turf_type': '',
                'description': 'Bamboo 2.4 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
            products.append({
                'product_name': 'Bamboo (1.8m)',
                'turf_type': '',
                'description': 'Bamboo 1.8 metres',
                'stock': row[3],
                'price': 0,
                'image_urls': bamboo_images
            })
        elif row[0] == 'Peg (U-Pins/Nails)':
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': peg_images
            })
        elif row[0] == 'Adhesive Joining Tape':
            products.append({
                'product_name': 'Adhesive Joining Tape (15m)',
                'turf_type': '',
                'description': 'Adhesive Joining Tape',
                'stock': row[3],
                'price': 25.0,
                'image_urls': tape_images
            })
        elif row[0] == 'Black Pebbles':
            products.append({
                'product_name': 'Black Pebbles (20kg bag)',
                'turf_type': '',
                'description': 'Black Decorative Pebbles',
                'stock': row[3],
                'price': 18.0,
                'image_urls': pebbles_images
            })
        elif row[0] == 'White Pebbles':
            products.append({
                'product_name': 'White Pebbles (20kg bag)',
                'turf_type': '',
                'description': 'White Decorative Pebbles',
                'stock': row[3],
                'price': 15.0,
                'image_urls': pebbles_images
            })
        else:
            # For any other product, fallback to DB images
            products.append({
                'product_name': row[0],
                'turf_type': row[1],
                'description': row[2],
                'stock': row[3],
                'price': row[4],
                'image_urls': image_urls
            })
    return render_template('products_list.html', 
                           products=rows,
                           bamboo_2m_stock=bamboo_2m_stock,
                           bamboo_2m_price=bamboo_2m_price,
                           bamboo_24m_stock=bamboo_24m_stock,
                           bamboo_24m_price=bamboo_24m_price,
                           bamboo_18m_stock=bamboo_18m_stock,
                           bamboo_18m_price=bamboo_18m_price,
                           pebbles_black_stock=pebbles_black_stock,
                           pebbles_black_price=pebbles_black_price,
                           pebbles_white_stock=pebbles_white_stock,
                           pebbles_white_price=pebbles_white_price,
                           fountain_stock=fountain_stock,
                           fountain_price=fountain_price,
                           premium_stock=premium_stock,
                           premium_price=premium_price,
                           green_lush_stock=green_lush_stock,
                           green_lush_price=green_lush_price,
                           natural_40mm_stock=natural_40mm_stock,
                           natural_40mm_price=natural_40mm_price,
                           golf_turf_stock=golf_turf_stock,
                           golf_turf_price=golf_turf_price,
                           imperial_lush_stock=imperial_lush_stock,
                           imperial_lush_price=imperial_lush_price,
                           pegs_stock=pegs_stock,
                           pegs_price=pegs_price,
                           artificial_hedges_stock=artificial_hedges_stock,
                           artificial_hedges_price=artificial_hedges_price,
                           adhesive_tape_stock=adhesive_tape_stock,
                           adhesive_tape_price=adhesive_tape_price,
                           bamboo_images=bamboo_images,
                           pebbles_images=pebbles_images,
                           fountain_images=fountain_images,
                           imperial_lush_images=imperial_lush_images,
                           green_lush_images=green_lush_images,
                           natural_40mm_images=natural_40mm_images,
                           golf_turf_images=golf_turf_images,
                           premium_turf_images=premium_turf_images,
                           artificial_hedges_images=artificial_hedges_images,
                           peg_images=peg_images,
                           tape_images=tape_images)

@app.route('/quotes', methods=['GET', 'POST'])
def quotes():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('quotes'):
        return redirect(url_for('access_restricted'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))


    if request.method == 'POST':
        # Handle form submission
        client_name = request.form.get('client_name')
        turf_type = request.form.get('turf_type')
        area_in_sqm_str = request.form.get('area_in_sqm')
        other_products = request.form.get('other_products')
        pebbles_custom_type = request.form.get('pebbles_custom_type')
        pebbles_qty = request.form.get('pebbles_qty', type=int)
        other_product_quantity = request.form.get('other_product_quantity', type=int)
        custom_price = request.form.get('custom_price', type=float)

        # Calculate total price
        # Fetch all product prices from DB for dynamic pricing
        c = sqlite3.connect('users.db').cursor()
        c.execute('SELECT product_name, price FROM products')
        price_table = {}
        for row in c.fetchall():
            try:
                price_table[row[0]] = float(row[1]) if row[1] else 0.0
            except (ValueError, TypeError):
                # Handle non-numeric prices like "Custom"
                price_table[row[0]] = 0.0

        try:
            area_in_sqm = float(area_in_sqm_str) if area_in_sqm_str else 0.0
        except ValueError:
            area_in_sqm = 0.0

        base_price = price_table.get(turf_type, 0) * area_in_sqm
        other_product_price = 0
        other_products_display = other_products
        if other_products == 'Fountain':
            other_product_price = custom_price or 0
        elif other_products == 'Pebbles':
            if pebbles_custom_type and pebbles_custom_type.lower() in ['multicolour', 'glow']:
                pebble_price = price_table.get('Pebbles Multicolour/Glow', 0)
            else:
                pebble_price = price_table.get('Pebbles Standard', 0)
            other_product_price = (pebble_price if pebbles_qty else 0) * (pebbles_qty or 0)
            other_products_display = f"Pebbles ({pebbles_custom_type}): {pebbles_qty}"
        elif other_products:
            other_product_price = price_table.get(other_products, 0) * (other_product_quantity or 0)

        total_price = base_price + other_product_price

        # Store in database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO quotes (client_name, turf_type, area_in_sqm, other_products, total_price, owner_id)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                         (client_name, turf_type, area_in_sqm, other_products_display, total_price, user_id))
            conn.commit()
            print(f"Quote saved: {client_name}, {turf_type}, {area_in_sqm}, {other_products_display}, {total_price}, {user_id}")
        except Exception as e:
            print(f"Error saving quote: {e}")
        # Fetch all quotes for this user
        c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
        quotes = c.fetchall()
        conn.close()

        summary = {
            'client_name': client_name,
            'turf_type': turf_type,
            'area_in_sqm': area_in_sqm,
            'other_products': other_products_display or 'None',
            'total_price': total_price
        }
        # Also fetch for payments page
        # No redirect, just render as before
        return render_template('quotes.html', success=True, quotes=quotes, summary=summary)

    # For GET or if not POST, just show all quotes
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
    quotes = c.fetchall()
    conn.close()
    return render_template('quotes.html', quotes=quotes)
@app.route('/payments')
def payments():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    import json

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Get invoices data for payments including extras_json - SHOW ALL INVOICES
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT invoices.id, clients.client_name, invoices.status, invoices.created_date,
                  invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.extras_json
                  FROM invoices
                  LEFT JOIN clients ON invoices.client_id = clients.id
                  ORDER BY invoices.id ASC''')
    invoices_data = c.fetchall()

    # Debug: Let's see what invoices exist
    print(f"DEBUG - Payments page for user {session.get('user_name')}:")
    print(f"  Found {len(invoices_data)} invoices total")
    if invoices_data:
        print(f"  First invoice: {invoices_data[0]}")
        statuses = [inv[2] for inv in invoices_data]
        print(f"  Invoice statuses: {statuses}")
        totals = [inv[8] for inv in invoices_data if inv[8]]
        print(f"  Invoice totals: {totals}")
        print(f"  Sum of all totals: {sum(float(t) for t in totals if t)}")

    # Get clients data
    c.execute('SELECT * FROM clients')  # Removed owner_id restriction - all users see all clients
    clients_data = c.fetchall()

    # Get quotes data
    c.execute('SELECT * FROM quotes WHERE owner_id = ?', (user_id,))
    quotes_data = c.fetchall()

    conn.close()

    # Format the data for the template
    invoices = []
    for invoice in invoices_data:
        status = invoice[2]
        # Parse extras_json
        extras = {}
        if invoice[9]:
            try:
                extras = json.loads(invoice[9])
            except json.JSONDecodeError:
                extras = {}

        invoices.append({
            'id': invoice[0],
            'client_name': invoice[1],
            'status': status,
            'due_date': invoice[3],
            'product': invoice[4],
            'quantity': invoice[5],
            'price': float(invoice[6]) if invoice[6] else 0.0,
            'gst': float(invoice[7]) if invoice[7] else 0.0,
            'total': float(invoice[8]) if invoice[8] else 0.0,
            'extras': extras
        })

    # Format clients data
    clients = []
    for client in clients_data:
        clients.append({
            'id': client[0],
            'client_name': client[1],
            'email': client[2] or '',
            'phone': client[3] or '',
            'account_type': client[4] or '',
            'company_name': client[5] or '',
            'actions': client[6] or ''
        })

    # Format quotes data
    quotes = []
    for quote in quotes_data:
        quotes.append({
            'id': quote[0],
            'client_name': quote[1],
            'turf_type': quote[2],
            'area_in_sqm': quote[3],
            'other_products': quote[4] or 'None',
            'total_price': float(quote[5]) if quote[5] else 0.0
        })

    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('payments.html', invoices=invoices, clients=clients, quotes=quotes, current_date=current_date)

@app.route('/calendar')
def calendar():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('calendar'):
        return redirect(url_for('access_restricted'))

    # Get current date for calendar navigation
    actual_today = datetime.now().date()
    current_year = request.args.get('year', actual_today.year, type=int)
    current_month = request.args.get('month', actual_today.month, type=int)
    current_day = request.args.get('day', actual_today.day, type=int)
    view = request.args.get('view', 'month')

    # Create current date object
    current_date = datetime(current_year, current_month, current_day)

    # Fetch tasks from the database for the calendar view
    tasks = get_all_tasks()

    # Map task statuses to colors
    status_colors = {
        'Not completed': 'red',
        'In Progress': 'orange',
        'Completed': 'green'
    }

    # Organize tasks by date
    tasks_by_date = {}
    for task in tasks:
        task_date = datetime.strptime(task[3], '%Y-%m-%d').date()
        task_color = status_colors.get(task[7], 'gray')  # task[7] is status
        task = list(task)
        task.append(task_color)  # task[9] = color
        if task_date not in tasks_by_date:
            tasks_by_date[task_date] = []
        tasks_by_date[task_date].append(task)

    # Prepare data for rendering based on view
    calendar_data = []
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    full_day_tasks = []

    if view == 'month':
        cal = Calendar(firstweekday=6)  # Set Sunday as the first day of the week
        days = cal.itermonthdays(current_year, current_month)
        # Adjust today to current_date for consistency with navigation
        today = current_date.date()
        for day in days:
            if day == 0:
                calendar_data.append({'day': None, 'tasks': [], 'is_today': False})
            else:
                date = datetime(current_year, current_month, day).date()
                is_today = (date == today)
                calendar_data.append({'day': day, 'tasks': tasks_by_date.get(date, []), 'is_today': is_today})
        header_text = month_names[current_month - 1]
    elif view == 'week':
        # Fix weekly view to start on Sunday and show correct tasks
        # Python's weekday(): Monday=0, Sunday=6
        weekday = current_date.weekday()
        # Calculate days to subtract to get to Sunday (weekday 6)
        days_to_sunday = (weekday + 1) % 7
        start_of_week = current_date - timedelta(days=days_to_sunday)
        end_of_week = start_of_week + timedelta(days=6)
        for i in range(7):
            date = start_of_week + timedelta(days=i)
            is_today = (date.date() == actual_today)
            calendar_data.append({'day': date.day, 'tasks': tasks_by_date.get(date.date(), []), 'is_today': is_today})
        start_suffix = 'th' if 11 <= start_of_week.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(start_of_week.day % 10, 'th')
        end_suffix = 'th' if 11 <= end_of_week.day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(end_of_week.day % 10, 'th')
        if start_of_week.month == end_of_week.month and start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix} - {end_of_week.day}{end_suffix})"
        elif start_of_week.year == end_of_week.year:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
        else:
            header_text = f"{month_names[start_of_week.month - 1]} ({start_of_week.day}{start_suffix}) - {month_names[end_of_week.month - 1]} ({end_of_week.day}{end_suffix})"
    elif view == 'day':
        tasks_by_hour = {hour: [] for hour in range(24)}
        full_day_tasks = []
        for task in tasks_by_date.get(current_date.date(), []):
            if task[4]:  # task_time
                try:
                    hour = int(task[4].split(':')[0])
                    tasks_by_hour[hour].append(task)
                except ValueError:
                    pass
            else:
                full_day_tasks.append(task)
        calendar_data = [{'hour': 'All Day', 'tasks': full_day_tasks}] + [{'hour': hour, 'tasks': tasks_by_hour[hour]} for hour in range(24)]
        # Fix the day view header to show correct day of week for the current_date
        day_of_week = current_date.strftime('%A')
        header_text = f"{month_names[current_month - 1]} {current_day} ({day_of_week})"
        current_date_str = current_date.strftime('%Y-%m-%d')

    # Fetch all users for assignment dropdown
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM users ORDER BY name')
    users = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return render_template('calendar.html',
                           calendar_data=calendar_data,
                           current_year=current_year,
                           current_month=current_month,
                           current_day=current_day,
                           header_text=header_text,
                           month_names=month_names,
                           view=view,
                           tasks=tasks,
                           full_day_tasks=full_day_tasks,
                           current_date=current_date_str if view == 'day' else None,
                           users=users)



@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
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
        actions = request.form.get('actions', '').strip()

        # Validate input
        import re
        if not re.match(r'^[A-Za-z ]+$', contact_name):
            conn.close()
            return render_template('edit_client.html', error='Contact name must contain only alphabetic characters and spaces.', client=client)
        if phone_number and not phone_number.isdigit():
            conn.close()
            return render_template('edit_client.html', error='Phone number must contain digits only.', client=client)
        if account_type not in ['Active', 'Deactivated']:
            conn.close()
            return render_template('edit_client.html', error='Invalid account type.', client=client)
        if '@' not in email or '.' not in email:
            conn.close()
            return render_template('edit_client.html', error='Invalid email format.', client=client)

        # Update client in database
        c.execute('''UPDATE clients SET client_name=?, phone=?, account_type=?, company_name=?, email=?, actions=? WHERE id=?''',
                  (contact_name, phone_number, account_type, company_name, email, actions, client_id))
        conn.commit()
        conn.close()

        # Redirect to clients and invoices list with clients tab active
        return redirect(url_for('payments') + '#clients')

    c.execute('SELECT id, client_name, phone, account_type, company_name, email, actions FROM clients WHERE id = ?', (client_id,))
    client = c.fetchone()
    conn.close()

    if not client:
        return render_template('edit_client.html', error="Client not found.")

    return render_template('edit_client.html', client=client)

# Task management API endpoints
@app.route('/api/tasks', methods=['GET'])
def get_all_tasks_api():
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
            'end_time': task[5],
            'location': task[6],
            'status': task[7],
            'created_at': task[8],
            'assigned_user_id': task[9] if len(task) > 9 else None
       
        })

    return jsonify(task_list)

@app.route('/api/tasks', methods=['POST'], endpoint='add_task_api')
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
    task_end_time = data.get('end_time', '')
    location = data.get('location', '')
    status = data.get('status', 'Not completed')
    assigned_user_id = data.get('assigned_user_id')
    owner_id = session.get('user_id')

    if not title or not task_date:
        print("Task creation failed: Title and date are required.")
        return jsonify({'error': 'Title and date are required'}), 400

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO tasks (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (title, description, task_date, task_time, task_end_time, location, status, assigned_user_id if assigned_user_id else None, owner_id))
        task_id = c.lastrowid  # Get the ID of the newly added task
        conn.commit()
        print(f"Task added successfully: {title} with ID {task_id}.")
        conn.close()
        return jsonify({'message': 'Task added successfully', 'task_id': task_id}), 201
    except Exception as e:
        print(f"Error adding task: {str(e)}")
        conn.close()
        return jsonify({'error': 'Failed to add task'}), 500
@app.route('/api/users')
def api_users():
    if 'user_name' not in session:
        return jsonify([])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, name, role FROM users ORDER BY name')
    users = [{'id': row[0], 'name': row[1], 'role': row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = c.fetchone()
    conn.close()

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify({
        'id': task[0],
        'title': task[1],
        'description': task[2],
        'date': task[3],
        'time': task[4],
        'end_time': task[5],
        'location': task[6],
        'status': task[7],
        'created_at': task[8]
    })

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'user_name' not in session:
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
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('clients'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()

    # Reset Account ID to 1 if no other clients exist
    cur = c.execute('SELECT COUNT(*) FROM clients')
    count = cur.fetchone()[0]
    if count == 0:
        # Reset the sqlite_sequence for clients table to 0
        c.execute("DELETE FROM sqlite_sequence WHERE name='clients'")
        conn.commit()

    conn.close()

    return redirect(url_for('payments'))

@app.route('/invoices/edit/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))
    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    # Define price table for products (ensure values are JSON serializable)
    price_table = {
        'Golden Imperial Lush': 45.0,
        'Golden Green Lush': 43.0,
        'Golden Natural 40mm': 47.0,
        'Golden Golf Turf': 50.0,
        'Golden Premium Turf': 52.0
    }

    if request.method == 'POST':
        client_name = request.form.get('client_name', '').strip()
        product = request.form.get('product', '').strip()
        quantity = request.form.get('quantity', type=float)
        price = request.form.get('price', type=float)
        gst_checkbox = request.form.get('gst_checkbox') == 'yes'
        status = request.form.get('status', '')

        # Fetch invoice before validation to avoid UnboundLocalError
        c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.status, invoices.created_date
                     FROM invoices
                     LEFT JOIN clients ON invoices.client_id = clients.id
                     WHERE invoices.id = ?''', (invoice_id,))
        invoice = c.fetchone()

        # Validate input
        if not client_name or not product or quantity is None or price is None:
            conn.close()
            return render_template('edit_invoice.html', error='All fields are required.', invoice=invoice, clients=clients, products=products, price_table=price_table)
        if status not in ['Paid', 'Unpaid']:
            conn.close()
            return render_template('edit_invoice.html', error='Invalid status.', invoice=invoice, clients=clients, products=products, price_table=price_table)

        # Calculate GST and total
        gst = price * 0.10 if gst_checkbox else 0
        total = price + gst

        # Get client_id from client_name
        c.execute('SELECT id FROM clients WHERE client_name = ?', (client_name,))
        client_row = c.fetchone()
        client_id = client_row[0] if client_row else None

        if not client_id:
            conn.close()
            return render_template('edit_invoice.html', error='Client not found.', invoice=invoice, clients=clients, products=products, price_table=price_table)

        # Update invoice in database
        c.execute('''UPDATE invoices SET client_id=?, product=?, quantity=?, price=?, gst=?, total=?, status=? WHERE id=?''',
                  (client_id, product, quantity, price, gst, total, status, invoice_id))
        conn.commit()
        conn.close()

        # Redirect to payments with invoices tab active
        return redirect(url_for('payments') + '#invoices')

    c.execute('''SELECT invoices.id, clients.client_name, invoices.product, invoices.quantity, invoices.price, invoices.gst, invoices.total, invoices.status, invoices.created_date
                 FROM invoices
                 LEFT JOIN clients ON invoices.client_id = clients.id
                 WHERE invoices.id = ?''', (invoice_id,))
    invoice = c.fetchone()

    # Fetch client list for autocomplete
    c.execute('SELECT client_name FROM clients')
    clients = [row[0] for row in c.fetchall()]

    # Fetch product list for dropdown
    c.execute('SELECT product_name FROM products')
    products = [row[0] for row in c.fetchall()]

    conn.close()

    if not invoice:
        return render_template('edit_invoice.html', error="Invoice not found.")

    return render_template('edit_invoice.html', invoice=invoice, clients=clients, products=products, price_table=price_table)

def resequence_invoice_ids():
    """Resequence all invoice IDs to start from 1 with no gaps"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Get all invoices ordered by creation date to maintain chronological order
    c.execute('SELECT * FROM invoices ORDER BY created_date ASC')
    invoices = c.fetchall()
    
    if not invoices:
        conn.close()
        return
    
    print(f"Resequencing {len(invoices)} invoices...")
    
    # Delete all invoices temporarily
    c.execute('DELETE FROM invoices')
    
    # Re-insert with sequential IDs starting from 1
    for index, invoice in enumerate(invoices, start=1):
        old_id = invoice[0]  # Original ID
        # Reconstruct the invoice with new ID (without discount column)
        new_values = (
            index,           # new id
            invoice[1],      # client_id
            invoice[2],      # product
            invoice[3],      # quantity
            invoice[4],      # price
            invoice[5],      # gst
            invoice[6],      # total
            invoice[7],      # status
            invoice[8],      # created_date
            invoice[9],      # extras_json
            invoice[10]      # owner_id
        )
        c.execute('''INSERT INTO invoices (id, client_id, product, quantity, price, gst, total, status, created_date, extras_json, owner_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', new_values)
        print(f"Resequenced invoice: {old_id} -> {index}")
    
    conn.commit()
    conn.close()
    print("Resequencing complete!")

@app.route('/invoices/delete/<int:invoice_id>', methods=['POST'])
def delete_invoice(invoice_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('payments'):
        return redirect(url_for('access_restricted'))
    if 'user_name' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()
    
    # Resequence all IDs after deletion
    resequence_invoice_ids()
    print(f"Deleted invoice {invoice_id} and resequenced all IDs")

    return redirect(url_for('payments'))

@app.route('/quotes/delete/<int:quote_id>', methods=['POST'])
def delete_quote(quote_id):
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if not has_permission('quotes'):
        return redirect(url_for('access_restricted'))

    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('DELETE FROM quotes WHERE id = ? AND owner_id = ?', (quote_id, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for('quotes'))

@app.route('/add_task', methods=['POST'], endpoint='add_task_form')
def add_task():
    if 'user_name' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not has_permission('calendar'):
        return jsonify({'error': 'Access restricted'}), 403
    if 'user_name' not in session:
        return redirect(url_for('login'))

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

@app.route('/verify_code/<email>', methods=['GET', 'POST'])
def verify_code(email):
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not code:
            return render_template('verify_code.html', email=email, error='Please enter the verification code.')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, name, role, verification_code, token_expiry FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()

        if user and user[3] == code and datetime.now().strftime('%Y-%m-%d %H:%M:%S') < user[4]:
            # Successful verification
            # Redirect to reset password page instead of logging in
            return redirect(url_for('reset_password', email=email))
        else:
            return render_template('verify_code.html', email=email, error='Invalid or expired verification code.')

    return render_template('verify_code.html', email=email)

# Update user IDs to overwrite deleted ones
@app.route('/profiles/update_ids', methods=['POST'])
def update_user_ids():
    if 'user_name' not in session:
        return redirect(url_for('login'))

    if session.get('user_role') != 'admin':
        return redirect(url_for('access_restricted'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Fetch all users ordered by ID
    c.execute('SELECT id FROM users ORDER BY id')
    users = c.fetchall()

    # Reassign IDs sequentially
    for index, user in enumerate(users, start=1):
        c.execute('UPDATE users SET id = ? WHERE id = ?', (index, user[0]))

    conn.commit()
    conn.close()

    flash('User IDs updated successfully!')
    return redirect(url_for('profiles'))

if __name__ == "__main__":
    app.run(debug=True)