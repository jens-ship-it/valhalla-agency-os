
"""Access request model for storing user access requests"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from extensions.db import db


class AccessRequest(db.Model):
    """Model for storing user access requests"""
    
    __tablename__ = 'access_request'
    
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(120), nullable=False)
    company = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default='pending', nullable=False)  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_user_id = Column(Integer, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<AccessRequest {self.email}>'
    
    @property
    def full_name(self):
        """Return full name of requester"""
        return f"{self.first_name} {self.last_name}"
