"""Service ticket models for customer support"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship, foreign
from extensions.db import db


class ServiceTicket(db.Model):
    """Service ticket model for tracking customer support requests"""

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)

    # Polymorphic client relationship - can be organization or individual client
    client_type = Column(String(20), nullable=False)  # organization, individual
    client_id = Column(Integer, nullable=False)

    # Ticket management
    priority = Column(String(20), default='medium', nullable=False)  # low, medium, high, urgent
    status = Column(String(20), default='open', nullable=False)  # open, in_progress, waiting, resolved, closed

    # Assignments
    assigned_user_id = Column(Integer, ForeignKey('user.id'))
    created_by_user_id = Column(Integer, ForeignKey('user.id'))
    requester_contact_id = Column(Integer, ForeignKey('contact.id'))

    # Dates
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime)
    due_date = Column(Date)

    # Relationships
    assigned_user = relationship('User', foreign_keys=[assigned_user_id], back_populates='assigned_tickets')
    created_by_user = relationship('User', foreign_keys=[created_by_user_id], back_populates='created_tickets')
    requester_contact = relationship('Contact')
    notes = relationship('ServiceNote', back_populates='ticket', cascade='all, delete-orphan')
    contacts = relationship('Contact', secondary='service_ticket_contact', back_populates='service_tickets')

    # Polymorphic relationships - unidirectional to avoid circular reference
    organization_client = relationship('Entity',
                                      primaryjoin='and_(ServiceTicket.client_id==foreign(Entity.id), ServiceTicket.client_type=="organization")',
                                      viewonly=True)
    individual_client = relationship('Client',  # Updated to reference Client model
                                   primaryjoin='and_(ServiceTicket.client_id==foreign(Client.contact_id), ServiceTicket.client_type=="individual")',
                                   viewonly=True)

    def __repr__(self):
        return f'<ServiceTicket {self.id}: {self.title}>'

    @property
    def client(self):
        """Return the client object (organization or individual)"""
        if self.client_type == 'organization':
            return self.organization_client
        elif self.client_type == 'individual':
            return self.individual_client
        return None

    @property
    def client_name(self):
        """Return the client name"""
        client = self.client
        if client:
            return client.name if hasattr(client, 'name') else client.full_name
        return 'Unknown Client'

    @property
    def is_open(self):
        """Check if ticket is open"""
        return self.status in self.get_open_statuses()

    @property
    def is_overdue(self):
        """Check if ticket is overdue"""
        if not self.due_date or not self.is_open:
            return False
        return datetime.utcnow().date() > self.due_date

    @property
    def age_days(self):
        """Calculate days since ticket was created"""
        return (datetime.utcnow() - self.created_at).days

    @property
    def days_open(self):
        """Calculate days ticket has been open"""
        end_date = self.resolved_at or datetime.utcnow()
        return (end_date - self.created_at).days

    @classmethod
    def get_open_tickets(cls):
        """Return query for open tickets"""
        return cls.query.filter(cls.status.in_(cls.get_open_statuses()))

    @classmethod
    def get_by_priority(cls, priority):
        """Return tickets by priority"""
        return cls.query.filter_by(priority=priority)

    @classmethod
    def get_status_choices(cls):
        """Return status choices for forms"""
        return [
            ('not_started', 'Not Started'),
            ('started', 'Started'),
            ('started_waiting_on_someone_else', 'Started - Waiting on Someone Else'),
            ('complete_pending_confirmation', 'Complete - Pending Confirmation'),
            ('complete', 'Complete')
        ]

    @classmethod
    def get_priority_choices(cls):
        """Return priority choices for forms"""
        return [
            ('low', 'Low'),
            ('normal', 'Normal'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ]

    @classmethod
    def get_client_type_choices(cls):
        """Return client type choices for forms"""
        return [
            ('organization', 'Organization'),
            ('individual', 'Individual')
        ]

    @classmethod
    def get_open_statuses(cls):
        """Return list of statuses considered 'open'"""
        return ['not_started', 'started', 'started_waiting_on_someone_else']


class ServiceNote(db.Model):
    """Service note model for ticket updates and comments"""

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('service_ticket.id'), nullable=False)
    author_user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    body = Column(Text, nullable=False)
    is_internal = Column(String(10), default='false', nullable=False)  # internal notes vs customer-visible
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ticket = relationship('ServiceTicket', back_populates='notes')
    author = relationship('User')

    def __repr__(self):
        return f'<ServiceNote {self.id} for Ticket {self.ticket_id}>'

    @property
    def is_internal_note(self):
        """Check if note is internal only"""
        return self.is_internal.lower() == 'true'