"""Policy models for insurance products"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from extensions.db import db


class GroupPolicy(db.Model):
    """Group policy model for employer/organization insurance"""

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False)
    carrier_id = Column(Integer, ForeignKey('entity.id'), nullable=True)  # FK to insurer vendor

    # Policy details
    product_type = Column(String(50), nullable=False)  # medical, dental, vision, life, disability
    policy_number = Column(String(100))
    effective_date = Column(Date)
    renewal_date = Column(Date)

    # Coverage details
    funding = Column(String(50))  # fully_insured, self_funded, level_funded
    estimated_monthly_revenue = Column(Numeric(10, 2))  # Estimated monthly revenue from this policy
    status = Column(String(20), default='active', nullable=False)  # active, inactive, pending

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    entity = relationship('Entity', back_populates='group_policies', foreign_keys=[entity_id])
    carrier = relationship('Entity', foreign_keys=[carrier_id])

    def __repr__(self):
        return f'<GroupPolicy {self.policy_number} - {self.entity.name}>'

    @property
    def is_active(self):
        """Check if policy is currently active"""
        return self.status == 'active'

    @property
    def is_due_for_renewal(self):
        """Check if policy is due for renewal within 90 days"""
        if not self.renewal_date:
            return False
        days_to_renewal = (self.renewal_date - date.today()).days
        return 0 <= days_to_renewal <= 90


class IndividualPolicy(db.Model):
    """Individual policy model for personal insurance"""

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False)
    carrier_id = Column(Integer, ForeignKey('entity.id'), nullable=False)  # FK to insurer vendor

    # Policy details
    product_type = Column(String(50), nullable=False)  # life, disability, annuity, health
    policy_number = Column(String(100))
    face_amount = Column(Numeric(12, 2))  # Coverage amount
    premium_amount = Column(Numeric(10, 2))  # Premium amount
    premium_frequency = Column(String(20))  # monthly, quarterly, semi_annual, annual

    effective_date = Column(Date)
    maturity_date = Column(Date)
    status = Column(String(20), default='active', nullable=False)  # active, inactive, lapsed, paid_up

    # Corporate relationship fields
    is_corporate_related = Column(Boolean, default=False, nullable=False)  # Yes/No - default No
    corporate_entity_id = Column(Integer, ForeignKey('entity.id'), nullable=True)  # FK to related entity
    corporate_explanation = Column(String(200))  # COLI, ICHRA, etc.

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship('Client', back_populates='individual_policies')
    carrier = relationship('Entity', foreign_keys=[carrier_id])
    corporate_entity = relationship('Entity', foreign_keys=[corporate_entity_id])

    def __repr__(self):
        return f'<IndividualPolicy {self.policy_number} - {self.client.full_name}>'

    @property
    def is_active(self):
        """Check if policy is currently active"""
        return self.status == 'active'

    @property
    def annual_premium(self):
        """Calculate annual premium based on frequency"""
        if not self.premium_amount:
            return 0

        multipliers = {
            'monthly': 12,
            'quarterly': 4,
            'semi_annual': 2,
            'annual': 1
        }

        return float(self.premium_amount) * multipliers.get(self.premium_frequency, 1)