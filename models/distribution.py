
"""Distribution model for linking entities to broker partners"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from extensions.db import db


class Distribution(db.Model):
    """Links client entities to their broker partners"""
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entity.id'), nullable=False)  # Client organization
    broker_id = Column(Integer, ForeignKey('entity.id'), nullable=False)  # Broker partner entity
    relationship_type = Column(String(50), default='distribution', nullable=False)  # distribution, referral, etc.
    status = Column(String(20), default='active', nullable=False)  # active, inactive
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    client_entity = relationship('Entity', foreign_keys=[entity_id], back_populates='distribution_relationships')
    broker_entity = relationship('Entity', foreign_keys=[broker_id], back_populates='brokered_clients')
    
    def __repr__(self):
        return f'<Distribution {self.client_entity.name} -> {self.broker_entity.name}>'
    
    @property
    def broker_name(self):
        """Return broker entity name"""
        return self.broker_entity.name if self.broker_entity else 'Unknown Broker'
    
    @property
    def client_name(self):
        """Return client entity name"""
        return self.client_entity.name if self.client_entity else 'Unknown Client'
