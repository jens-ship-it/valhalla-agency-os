"""Demo request model for storing demo requests from landing page"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from extensions.db import db


class DemoRequest(db.Model):
    """Model for storing demo requests from public landing page"""
    
    __tablename__ = 'demo_request'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    company = Column(String(100), nullable=True)
    team_size = Column(String(50), nullable=True)  # 1-10, 11-50, 51-200, 201+
    notes = Column(Text, nullable=True)
    status = Column(String(20), default='pending', nullable=False)  # pending, contacted, converted
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<DemoRequest {self.email}>'
