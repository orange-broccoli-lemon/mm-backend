# app/models/person_follow.py

from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class PersonFollowModel(Base):
    __tablename__ = "person_follows"
    
    user_id = Column(BigInteger, ForeignKey('users.user_id'), primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.person_id'), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'person_id', name='unique_person_follow'),
    )
    
    def __repr__(self):
        return f"<PersonFollowModel(user_id={self.user_id}, person_id={self.person_id})>"
