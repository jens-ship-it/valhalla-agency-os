"""Utility decorators for RBAC and other common functionality"""
from functools import wraps
from flask import abort
from flask_login import current_user


def require_roles(*role_names):
    """Decorator to require specific roles for route access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_any_role(*role_names):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Decorator to require admin role"""
    return require_roles('admin')(f)


def service_or_admin_required(f):
    """Decorator to require service or admin role"""
    return require_roles('service', 'admin')(f)


def account_mgmt_or_admin_required(f):
    """Decorator to require account_mgmt or admin role"""
    return require_roles('account_mgmt', 'admin')(f)


def sales_or_admin_required(f):
    """Decorator to require sales or admin role"""
    return require_roles('sales', 'admin')(f)


def marketing_or_admin_required(f):
    """Decorator to require marketing or admin role"""
    return require_roles('marketing', 'admin')(f)


def role_required(*role_names):
    """Decorator to require any of the specified roles for route access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_any_role(*role_names):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
