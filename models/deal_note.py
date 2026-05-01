
"""Deal notes model for tracking sales progression"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from extensions.db import db


class DealNote(db.Model):
    """Deal note model for tracking sales deal progression"""
    __tablename__ = 'deal_note'

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deal.id'), nullable=False)
    author_user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    title = Column(String(200), nullable=True)  # Optional title for the note
    body = Column(Text, nullable=False)
    note_type = Column(String(50), default='general')  # 'general', 'call', 'meeting', 'email', 'follow_up'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship('Deal', back_populates='progress_notes')
    author = relationship('User')

    def __repr__(self):
        return f'<DealNote {self.id} for Deal {self.deal_id}>'

    @property
    def short_body(self):
        """Return truncated body for display"""
        if len(self.body) <= 100:
            return self.body
        return self.body[:97] + '...'
