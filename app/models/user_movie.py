# app/models/user_movie.py

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    Date,
    DateTime,
    UniqueConstraint,
    ForeignKey,
    Enum,
)
from sqlalchemy.sql import func
from app.database import Base
import enum


class WatchStatus(enum.Enum):
    watching = "watching"
    completed = "completed"
    plan_to_watch = "plan_to_watch"
    dropped = "dropped"


class UserMovieModel(Base):
    __tablename__ = "user_movies"

    user_movie_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    movie_id = Column(BigInteger, ForeignKey("movies.movie_id"), nullable=False)
    status = Column(Enum(WatchStatus), default=WatchStatus.completed)
    rating = Column(DECIMAL(2, 1), nullable=True)
    watched_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="unique_user_movie"),)

    def __repr__(self):
        return f"<UserMovieModel(user_id={self.user_id}, movie_id={self.movie_id})>"
