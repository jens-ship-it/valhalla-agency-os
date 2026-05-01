"""Sales pipeline models"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from extensions.db import db


class Deal(db.Model):
    """Sales deal/opportunity model"""

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    # Client relationships - can be either organization or individual contact
    entity_id = Column(Integer, ForeignKey('entity.id'))
    contact_id = Column(Integer, ForeignKey('contact.id'), nullable=True)  # Individual contact for sales

    # Deal details
    stage = Column(Integer, default=0, nullable=False)  # 0, 1, 2, 3, 4, 5
    owner_user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    est_close_date = Column(Date)
    est_premium_value = Column(Numeric(12, 2))
    recurring = Column(String(20), nullable=False, default='Recurring')  # 'Recurring' or 'Nonrecurring'
    actual_close_date = Column(Date)

    # Additional details
    product_type = Column(String(100))  # e.g., "Group Medical", "Individual Life"
    competition = Column(String(200))
    next_step = Column(Text)
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    entity = relationship('Entity', back_populates='deals')
    contact = relationship('Contact', back_populates='deals')  # Individual contact
    owner = relationship('User')
    progress_notes = relationship('DealNote', back_populates='deal', order_by='DealNote.created_at.desc()')

    def __repr__(self):
        client_name = self.entity.name if self.entity else (self.contact.full_name if self.contact else 'No Client')
        return f'<Deal {self.name} - {client_name}>'

    @property
    def client_name(self):
        """Return the client name (organization or individual)"""
        if self.entity:
            return self.entity.name
        elif self.contact:
            return self.contact.full_name
        return 'Unknown Client'

    @property
    def is_open(self):
        """Check if deal is still open (stages 0-4)"""
        return self.stage < 5

    @property
    def is_overdue(self):
        """Check if deal is past estimated close date"""
        if not self.est_close_date or not self.is_open:
            return False
        return date.today() > self.est_close_date

    @property
    def stage_name(self):
        """Return human-readable stage name"""
        stage_names = {
            0: 'Lead',
            1: 'Qualified',
            2: 'Proposal',
            3: 'Negotiation',
            4: 'Verbal Agreement',
            5: 'Closed'
        }
        return stage_names.get(self.stage, 'Unknown')

    @classmethod
    def get_open_deals(cls):
        """Return query for open deals (stages 0-4)"""
        return cls.query.filter(cls.stage < 5)

    @classmethod
    def get_deals_by_stage(cls, stage):
        """Return deals by stage"""
        return cls.query.filter_by(stage=stage)

    @classmethod
    def get_stage_choices(cls):
        """Return stage choices for forms"""
        return [
            (0, 'Lead'),
            (1, 'Qualified'),
            (2, 'Proposal'),
            (3, 'Negotiation'),
            (4, 'Verbal Agreement'),
            (5, 'Closed')
        ]