"""Center of Influence (COI) model for tracking contact influence relationships"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from extensions.db import db


class COI(db.Model):
    """Center of Influence model for tracking why contacts are influential"""

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contact.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)

    # COI Classification
    category = Column(String(50), nullable=False)  # CPA, attorney, NYU, PSU, local_friend, phi_tau, etc.

    # Notes and context
    explanation = Column(Text)  # Detailed explanation of the COI relationship
    notes = Column(Text)  # Additional notes about interactions, history, etc.

    # Status tracking
    status = Column(String(20), default='active', nullable=False)  # active, inactive
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contact = relationship('Contact', back_populates='coi_records')
    user = relationship('User', backref='managed_coi_records')

    def __repr__(self):
        return f'<COI {self.contact.full_name} - {self.category}>'

    @property
    def contact_name(self):
        """Return the contact's full name"""
        return self.contact.full_name if self.contact else 'Unknown Contact'

    @property
    def is_active(self):
        """Check if COI record is currently active"""
        return self.status == 'active'

    @classmethod
    def get_active(cls):
        """Return query for active COI records"""
        return cls.query.filter_by(status='active')

    @classmethod
    def get_by_contact(cls, contact_id):
        """Get all COI records for a specific contact"""
        return cls.query.filter_by(contact_id=contact_id, status='active')

    @classmethod
    def get_by_category(cls, category):
        """Get COI records by category"""
        return cls.query.filter_by(category=category, status='active')

    @staticmethod
    def get_category_choices():
        """Return available COI categories"""
        return [
            ('CPA', 'CPA'),
            ('attorney', 'Attorney'),
            ('NYU', 'NYU Alumni'),
            ('PSU', 'PSU Alumni'),
            ('local_friend', 'Local Friend'),
            ('greek_organization', 'Greek Organization'),
            ('financial_advisor', 'Financial Advisor'),
            ('real_estate', 'Real Estate Professional'),
            ('banker', 'Banker'),
            ('business_owner', 'Business Owner'),
            ('healthcare', 'Healthcare Professional'),
            ('other_professional', 'Other Professional'),
            ('family', 'Family'),
            ('client', 'Existing Client'),
            ('vendor', 'Vendor/Supplier'),
            ('other', 'Other')
        ]