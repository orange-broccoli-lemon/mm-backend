# app/models/movie.py

from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, Boolean, DECIMAL, DateTime
from sqlalchemy.sql import func
from app.database import Base

class MovieModel(Base):
    """영화 테이블 모델"""
    __tablename__ = "movies"
    
    movie_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, nullable=True)
    imdb_id = Column(String(20), unique=True, nullable=True)
    title = Column(String(255), nullable=False)
    original_title = Column(String(255), nullable=True)
    overview = Column(Text, nullable=True)
    release_date = Column(Date, nullable=True)
    runtime = Column(Integer, nullable=True)
    poster_url = Column(Text, nullable=True)
    backdrop_url = Column(Text, nullable=True)
    average_rating = Column(DECIMAL(3, 2), default=0.00)
    is_adult = Column(Boolean, default=False)
    trailer_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<MovieModel(id={self.movie_id}, tmdb_id={self.tmdb_id}, title='{self.title}')>"
