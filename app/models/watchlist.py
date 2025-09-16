# app/models/watchlist.py

from sqlalchemy import Column, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class WatchlistModel(Base):
    __tablename__ = "watchlists"
    
    user_id = Column(BigInteger, ForeignKey('users.user_id'), primary_key=True)
    movie_id = Column(Integer, ForeignKey('movies.movie_id'), primary_key=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='unique_watchlist'),
    )
    
    def __repr__(self):
        return f"<WatchlistModel(user_id={self.user_id}, movie_id={self.movie_id})>"
