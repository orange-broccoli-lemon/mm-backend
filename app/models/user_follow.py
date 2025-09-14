# app/models/user_follow.py

from sqlalchemy import Column, BigInteger, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class UserFollowModel(Base):
    __tablename__ = "user_follows"
    
    follow_id = Column(BigInteger, primary_key=True, autoincrement=True)
    follower_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    following_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
    )
    
    def __repr__(self):
        return f"<UserFollowModel(follower={self.follower_id}, following={self.following_id})>"
