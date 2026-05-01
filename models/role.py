"""Role model for RBAC system"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from extensions.db import db
from .user import user_roles


class Role(db.Model):
    """Role model for role-based access control"""
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    # Relationships
    users = relationship('User', secondary=user_roles, back_populates='roles')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    @classmethod
    def get_role_choices(cls):
        """Return list of tuples for WTForms SelectField"""
        return [(role.name, role.name.replace('_', ' ').title()) for role in cls.query.all()]
