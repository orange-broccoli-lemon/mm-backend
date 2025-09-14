# app/models/comment.py

from sqlalchemy import Column, BigInteger, Text, Boolean, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class CommentModel(Base):
    __tablename__ = "comments"
    
    comment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    movie_id = Column(BigInteger, ForeignKey('movies.movie_id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    content = Column(Text, nullable=False)
    is_spoiler = Column(Boolean, default=False)
    spoiler_confidence = Column(DECIMAL(4, 3), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<CommentModel(id={self.comment_id}, movie_id={self.movie_id})>"
