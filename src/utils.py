"""
Utility functions for the Autonomous Supply Chain Recovery Agent
"""

import logging
import os
import sys
import time
import json
import requests
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps

def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up logging for a module"""
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

        # Optionally add file handler
        try:
            file_handler = logging.FileHandler('supply_chain_agent.log')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass  # If we can't create file log, continue with console only

    return logger

def safe_request(method: str, url: str, **kwargs) -> Optional[requests.Response]:
    """Make a safe HTTP request with error handling"""
    try:
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30

        # Make the request
        response = requests.request(method, url, **kwargs)
        return response

    except requests.exceptions.ConnectionError as e:
        logging.getLogger(__name__).warning(f"Connection error for {method} {url}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logging.getLogger(__name__).warning(f"Timeout error for {method} {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.getLogger(__name__).warning(f"Request error for {method} {url}: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error in safe_request for {method} {url}: {e}")
        return None

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry a function on failure"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            _delay = delay
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries:
                        logging.getLogger(__name__).error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    else:
                        logging.getLogger(__name__).warning(f"Function {func.__name__} failed, retrying in {_delay}s... ({i+1}/{max_retries})")
                        time.sleep(_delay)
                        _delay *= backoff
            return None
        return wrapper
    return decorator

def timing_decorator(func: Callable) -> Callable:
    """Decorator to time function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            logging.getLogger(__name__).debug(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logging.getLogger(__name__).error(f"{func.__name__} failed after {execution_time:.4f} seconds: {e}")
            raise
    return wrapper

def singleton(cls):
    """Decorator to make a class a singleton"""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url: str) -> bool:
    """Basic URL validation"""
    import re
    pattern = r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z]{2,6}\b(?:[-a-zA-Z0-9@:%\_\+.~#?&\/=]*)$'
    return re.match(pattern, url) is not None

def format_timestamp(timestamp: Optional[datetime] = None) -> str:
    """Format a timestamp for display"""
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse a timestamp string"""
    try:
        # Try ISO format first
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except Exception:
        try:
            # Try common format
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change from old to new value"""
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf') if new_value > 0 else float('-inf')
    return ((new_value - old_value) / old_value) * 100

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max"""
    return max(min_val, min(max_val, value))

def normalize_to_range(value: float, old_min: float, old_max: float,
                      new_min: float = 0.0, new_max: float = 1.0) -> float:
    """Normalize a value from one range to another"""
    if old_max == old_min:
        return new_min
    normalized = (value - old_min) / (old_max - old_min)
    return new_min + (normalized * (new_max - new_min))

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers"""
    return numerator / denominator if denominator != 0 else default

def load_json_file(filepath: str) -> Optional[Dict[Any, Any]]:
    """Load JSON from a file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.getLogger(__name__).warning(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        logging.getLogger(__name__).error(f"Invalid JSON in {filepath}: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error loading {filepath}: {e}")
        return None

def save_json_file(data: Dict[Any, Any], filepath: str) -> bool:
    """Save data as JSON to a file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logging.getLogger(__name__).error(f"Error saving {filepath}: {e}")
        return False

def get_environment_variable(name: str, default: Any = None) -> Any:
    """Get environment variable with optional default"""
    return os.environ.get(name, default)

def is_development_environment() -> bool:
    """Check if we're in a development environment"""
    env = get_environment_variable('ENVIRONMENT', 'production').lower()
    return env in ['development', 'dev', 'test', 'testing']

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID"""
    import uuid
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix if len(suffix) < max_length else text[:max_length]