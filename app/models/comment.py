# app/models/comment.py

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    Text,
    Boolean,
    DECIMAL,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.sql import func
from app.database import Base


class CommentModel(Base):
    __tablename__ = "comments"

    comment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(DECIMAL(3, 1), nullable=True)
    watched_date = Column(Date, nullable=True)

    is_spoiler = Column(Boolean, default=False, nullable=False)
    spoiler_confidence = Column(DECIMAL(4, 3), nullable=True)
    is_positive = Column(Boolean, default=None, nullable=True)
    positive_confidence = Column(DECIMAL(4, 3), nullable=True)
    is_toxic = Column(Boolean, default=None, nullable=True)
    toxic_confidence = Column(DECIMAL(4, 3), nullable=True)

    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return (
            f"<CommentModel(id={self.comment_id}, movie_id={self.movie_id}, rating={self.rating})>"
        )
