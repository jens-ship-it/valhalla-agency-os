"""Contact models for universal contact management"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Table, UniqueConstraint, Date
from sqlalchemy.orm import relationship, foreign
from extensions.db import db


class Contact(db.Model):
    """Universal contact model - replaces Individual model"""

    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    work_email = Column(String(120), index=True)
    personal_email = Column(String(120), index=True)
    phone = Column(String(20))
    mobile = Column(String(20))

    # Personal information (formerly in Individual model)
    dob = Column(Date)  # Date of birth

    # Address
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state = Column(String(50))
    zip = Column(String(20))

    notes = Column(Text)
    status = Column(String(20), default='active', nullable=False)  # active, inactive
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contact_links = relationship('ContactLink', back_populates='contact', cascade='all, delete-orphan')
    service_tickets = relationship('ServiceTicket', secondary='service_ticket_contact', back_populates='contacts')
    client_record = relationship('Client', back_populates='contact', uselist=False, cascade='all, delete-orphan')
    coi_records = relationship('COI', back_populates='contact', cascade='all, delete-orphan')
    deals = relationship('Deal', back_populates='contact', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Contact {self.full_name}>'

    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.zip]
        return ', '.join(filter(None, parts))

    @property
    def preferred_phone(self):
        """Return preferred phone number (mobile first, then phone)"""
        return self.mobile or self.phone

    @property
    def preferred_email(self):
        """Return preferred email (work first, then personal)"""
        return self.work_email or self.personal_email

    @property
    def is_client(self):
        """Return True if this contact has a client record"""
        return self.client_record is not None

    @classmethod
    def get_active(cls):
        """Return query for active contacts"""
        return cls.query.filter_by(status='active')

    @classmethod
    def get_clients(cls):
        """Return query for contacts that are clients"""
        return cls.query.join(Client).filter(cls.status == 'active')

    @classmethod
    def search(cls, query_string):
        """Search contacts by name or email"""
        return cls.query.filter(
            db.or_(
                cls.first_name.ilike(f'%{query_string}%'),
                cls.last_name.ilike(f'%{query_string}%'),
                cls.work_email.ilike(f'%{query_string}%'),
                cls.personal_email.ilike(f'%{query_string}%')
            )
        )


class Client(db.Model):
    """Client-specific data for contacts who are insurance clients"""

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contact.id'), nullable=False, unique=True)
    ssn_last4 = Column(String(4))  # Last 4 digits of SSN for identification
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contact = relationship('Contact', back_populates='client_record')
    individual_policies = relationship('IndividualPolicy', back_populates='client', cascade='all, delete-orphan')
    service_tickets = relationship('ServiceTicket',
                                 primaryjoin='and_(Client.contact_id==foreign(ServiceTicket.client_id), ServiceTicket.client_type=="individual")',
                                 viewonly=True)



    def __repr__(self):
        return f'<Client {self.contact.full_name}>'

    @property
    def full_name(self):
        """Return full name from contact"""
        return self.contact.full_name

    @property
    def active_policies_count(self):
        """Return count of active individual policies"""
        return len([p for p in self.individual_policies if p.status == 'active'])

    @classmethod
    def get_active(cls):
        """Return query for active clients"""
        return cls.query.join(Contact).filter(Contact.status == 'active')

    @classmethod
    def search(cls, query_string):
        """Search clients by contact name or email"""
        return cls.query.join(Contact).filter(
            db.or_(
                Contact.first_name.ilike(f'%{query_string}%'),
                Contact.last_name.ilike(f'%{query_string}%'),
                Contact.email.ilike(f'%{query_string}%')
            )
        )


class ContactLink(db.Model):
    """Link between contacts and entities with proper foreign key constraint"""

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey('contact.id'), nullable=False)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False)
    role_at_entity = Column(String(100))  # e.g., "Benefits Lead", "HR Director", "CFO"
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint to prevent duplicate links
    __table_args__ = (UniqueConstraint('contact_id', 'entity_id'),)

    # Relationships
    contact = relationship('Contact', back_populates='contact_links')
    entity = relationship('Entity', back_populates='contact_links')

    def __repr__(self):
        return f'<ContactLink {self.contact.full_name} -> {self.entity.name}>'

    @property
    def entity_name(self):
        """Return the entity name"""
        return self.entity.name if self.entity else 'Unknown Entity'

    @property
    def entity_type(self):
        """Return the entity type"""
        return self.entity.entity_type if self.entity else 'unknown'





# Association table for many-to-many relationship between service tickets and contacts
service_ticket_contact = Table(
    'service_ticket_contact',
    db.Model.metadata,
    Column('id', Integer, primary_key=True),
    Column('ticket_id', Integer, ForeignKey('service_ticket.id'), nullable=False),
    Column('contact_id', Integer, ForeignKey('contact.id'), nullable=False),
    Column('relationship_label', String(100)),  # e.g., "requestor", "subject", "approver"
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
)