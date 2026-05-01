"""Entity model for unified organization and vendor management"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, foreign
from extensions.db import db


class Entity(db.Model):
    """Unified entity model for organizations, vendors, and other business entities"""

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)

    # Hierarchy support - for subsidiaries/affiliates
    parent_entity_id = Column(Integer, ForeignKey('entity.id'))

    # Organization fields
    fein = Column(String(20))  # Federal Employer Identification Number
    sic_code = Column(String(10))  # Standard Industrial Classification code
    industry = Column(String(100))
    is_applicable_large_employer = Column(Boolean, default=False, nullable=False)  # ACA ALE status

    # Common fields for all entities
    website = Column(String(200))  # Available to all entities
    status = Column(String(20), default='active', nullable=False)  # active, inactive

    # Contact information
    phone = Column(String(20))
    email = Column(String(120))

    # Address
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state = Column(String(50))
    zip = Column(String(20))

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    contact_links = relationship('ContactLink', back_populates='entity', cascade='all, delete-orphan')

    # Hierarchy relationships
    parent_entity = relationship('Entity', remote_side=[id], back_populates='subsidiaries')
    subsidiaries = relationship('Entity', back_populates='parent_entity', cascade='all, delete-orphan')

    # Organization relationships
    group_policies = relationship('GroupPolicy', back_populates='entity', foreign_keys='GroupPolicy.entity_id', cascade='all, delete-orphan')
    service_tickets = relationship('ServiceTicket', 
                                 primaryjoin='and_(Entity.id==foreign(ServiceTicket.client_id), ServiceTicket.client_type=="organization")',
                                 viewonly=True)

    deals = relationship('Deal', back_populates='entity')

    # Distribution relationships
    distribution_relationships = relationship('Distribution', foreign_keys='Distribution.entity_id', back_populates='client_entity', cascade='all, delete-orphan')
    brokered_clients = relationship('Distribution', foreign_keys='Distribution.broker_id', back_populates='broker_entity', cascade='all, delete-orphan')

    # Vendor relationship
    vendor_detail = relationship('VendorDetail', back_populates='entity', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Entity {self.name}>'

    # Relationships for distribution/brokerage
    distribution_relationships = relationship('Distribution', foreign_keys='Distribution.entity_id', back_populates='client_entity')
    brokered_clients = relationship('Distribution', foreign_keys='Distribution.broker_id', back_populates='broker_entity')

    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.address_line1, self.address_line2, self.city, self.state, self.zip]
        return ', '.join(filter(None, parts))

    @property
    def primary_contact(self):
        """Return primary contact from contact links"""
        primary_link = next((link for link in self.contact_links if link.is_primary), None)
        return primary_link.contact if primary_link else None

    @property
    def primary_contact_name(self):
        """Return primary contact name"""
        return self.primary_contact.full_name if self.primary_contact else None

    @property
    def contact_email(self):
        """Return primary contact work email or entity email"""
        return self.primary_contact.preferred_email if self.primary_contact else self.email

    @property
    def contact_phone(self):
        """Return primary contact phone or entity phone"""
        return self.primary_contact.preferred_phone if self.primary_contact else self.phone

    @property
    def is_organization(self):
        """Check if entity is an organization (no vendor detail)"""
        return self.vendor_detail is None

    @property
    def is_vendor(self):
        """Check if entity is a vendor (has vendor detail)"""
        return self.vendor_detail is not None

    @property
    def entity_type(self):
        """Return entity type based on vendor detail presence"""
        return 'vendor' if self.is_vendor else 'organization'

    @property
    def active_policies_count(self):
        """Return count of active group policies (for organizations)"""
        if self.is_organization:
            return len([p for p in self.group_policies if p.status == 'active'])
        return 0

    @property
    def is_subsidiary(self):
        """Check if entity is a subsidiary of another entity"""
        return self.parent_entity_id is not None

    @property
    def has_subsidiaries(self):
        """Check if entity has subsidiaries"""
        return len(self.subsidiaries) > 0

    @property
    def hierarchy_level(self):
        """Return the hierarchy level (0 for top-level, 1+ for subsidiaries)"""
        level = 0
        current = self
        while current.parent_entity_id:
            level += 1
            current = current.parent_entity
        return level

    @property
    def primary_broker(self):
        """Return primary broker partner for this entity"""
        active_relationships = [d for d in self.distribution_relationships if d.status == 'active']
        return active_relationships[0].broker_entity if active_relationships else None

    @property
    def is_broker_partner(self):
        """Check if entity is a broker partner"""
        return self.is_vendor and self.vendor_detail.vendor_type == 'broker_partner'

    @property
    def full_hierarchy_name(self):
        """Return full name with parent entity for subsidiaries"""
        if self.parent_entity:
            return f"{self.parent_entity.name} - {self.name}"
        return self.name

    @classmethod
    def get_active(cls):
        """Return query for active entities"""
        return cls.query.filter_by(status='active')

    @classmethod
    def get_organizations(cls):
        """Return query for organization entities (those without vendor details)"""
        return cls.query.outerjoin(VendorDetail).filter(
            VendorDetail.id.is_(None), 
            cls.status == 'active'
        )

    @classmethod
    def get_vendors(cls):
        """Return query for vendor entities (those with vendor details)"""
        return cls.query.join(VendorDetail).filter(cls.status == 'active')

    @classmethod
    def get_top_level(cls):
        """Return query for top-level entities (no parent)"""
        return cls.query.filter(cls.parent_entity_id.is_(None), cls.status == 'active')

    @classmethod
    def get_subsidiaries(cls, parent_id):
        """Return query for subsidiaries of a given parent entity"""
        return cls.query.filter_by(parent_entity_id=parent_id, status='active')

    @classmethod
    def search(cls, query_string, is_vendor=None):
        """Search entities by name"""
        query = cls.query.filter(cls.name.ilike(f'%{query_string}%'))
        if is_vendor is True:
            query = query.join(VendorDetail)
        elif is_vendor is False:
            query = query.outerjoin(VendorDetail).filter(VendorDetail.id.is_(None))
        return query


class VendorDetail(db.Model):
    """Vendor-specific details for entities that are vendors"""

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False, unique=True)
    vendor_type = Column(String(50), nullable=False)  # insurer, tpa, pbm, software_provider, consultant, attorney, other
    description = Column(Text)  # Description of vendor's services/capabilities
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    entity = relationship('Entity', back_populates='vendor_detail')

    def __repr__(self):
        return f'<VendorDetail {self.entity.name} ({self.vendor_type})>'

    @classmethod
    def get_vendor_type_choices(cls):
        """Return list of vendor type choices for forms"""
        return [
            ('insurer', 'Insurer'),
            ('tpa', 'TPA'),
            ('pbm', 'PBM'),
            ('software_provider', 'Software Provider'),
            ('broker_partner', 'Broker Partner'),
            ('consultant', 'Consultant'),
            ('attorney', 'Attorney'),
            ('other', 'Other')
        ]