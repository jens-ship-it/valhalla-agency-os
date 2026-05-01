"""User and Role models for authentication and authorization"""
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from extensions.db import db


# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    db.Model.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('role.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    created_tickets = relationship('ServiceTicket', foreign_keys='ServiceTicket.created_by_user_id', back_populates='created_by_user')
    assigned_tickets = relationship('ServiceTicket', foreign_keys='ServiceTicket.assigned_user_id', back_populates='assigned_user')
    service_notes = relationship('ServiceNote', back_populates='author')
    owned_deals = relationship('Deal', back_populates='owner')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        """Return full name of user"""
        return f"{self.first_name} {self.last_name}"
    
    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)
    
    def has_any_role(self, *role_names):
        """Check if user has any of the specified roles"""
        user_role_names = {role.name for role in self.roles}
        return bool(user_role_names.intersection(role_names))
    
    def has_admin_role(self):
        """Check if user has admin role"""
        return self.has_role('admin')
    
    def get_id(self):
        """Return user ID as string for Flask-Login"""
        return str(self.id)
