# app/models/comment_like.py

from sqlalchemy import Column, BigInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class CommentLikeModel(Base):
    __tablename__ = "comment_likes"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    comment_id = Column(BigInteger, ForeignKey("comments.comment_id"), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    def __repr__(self):
        return f"<CommentLikeModel(user_id={self.user_id}, comment_id={self.comment_id})>"
