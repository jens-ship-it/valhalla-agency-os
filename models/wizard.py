"""Wizard state model for multi-step form flows"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text
from extensions.db import db
import secrets


class WizardState(db.Model):
    """Server-side storage for wizard state to avoid storing PII in client session"""
    
    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    wizard_type = Column(String(50), nullable=False)  # e.g., 'individual_policy'
    user_id = Column(Integer, nullable=False)  # FK to user running the wizard
    step_data = Column(Text, nullable=False)  # JSON-serialized step data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f'<WizardState {self.wizard_type} - {self.token[:8]}...>'
    
    @classmethod
    def create_wizard(cls, wizard_type, user_id, expiry_hours=2):
        """Create a new wizard state with a secure token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        wizard = cls(
            token=token,
            wizard_type=wizard_type,
            user_id=user_id,
            step_data='{}',  # Start with empty JSON object
            expires_at=expires_at
        )
        
        db.session.add(wizard)
        db.session.commit()
        
        return wizard
    
    @classmethod
    def get_by_token(cls, token):
        """Get wizard by token if not expired"""
        wizard = cls.query.filter_by(token=token).first()
        
        if not wizard:
            return None
        
        # Check if expired
        if wizard.expires_at < datetime.utcnow():
            db.session.delete(wizard)
            db.session.commit()
            return None
        
        return wizard
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired wizard states"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for wizard in expired:
            db.session.delete(wizard)
        db.session.commit()
        return len(expired)
