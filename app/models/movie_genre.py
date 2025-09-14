# app/models/movie_genre.py

from sqlalchemy import Column, BigInteger, Integer, ForeignKey
from app.database import Base

class MovieGenreModel(Base):
    __tablename__ = "movie_genres"
    
    movie_id = Column(BigInteger, ForeignKey('movies.movie_id'), primary_key=True)
    genre_id = Column(Integer, ForeignKey('genres.genre_id'), primary_key=True)
    
    def __repr__(self):
        return f"<MovieGenreModel(movie_id={self.movie_id}, genre_id={self.genre_id})>"
