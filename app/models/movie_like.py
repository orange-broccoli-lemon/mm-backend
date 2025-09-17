# app/models/movie_like.py

from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class MovieLikeModel(Base):
    __tablename__ = "movie_likes"

    user_id = Column(BigInteger, ForeignKey("users.user_id"), primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp())

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="unique_movie_like"),)

    def __repr__(self):
        return f"<MovieLikeModel(user_id={self.user_id}, movie_id={self.movie_id})>"
