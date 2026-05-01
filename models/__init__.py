"""Models package - imports all models for SQLAlchemy registration"""
from .user import User
from .role import Role
from .entity import Entity, VendorDetail
from .contact import Contact, ContactLink, Client
from .coi import COI
from .policy import GroupPolicy, IndividualPolicy
from .service import ServiceTicket, ServiceNote
from .sales import Deal
from .deal_note import DealNote
from .demo_request import DemoRequest

__all__ = [
    'User', 'Role', 'Entity', 'VendorDetail', 'Contact', 'ContactLink', 'Client',
    'COI', 'GroupPolicy', 'IndividualPolicy', 'ServiceTicket', 'ServiceNote', 'Deal', 'DealNote',
    'DemoRequest'
]