# app/models/movie_cast.py

from sqlalchemy import Column, BigInteger, String, ForeignKey, Enum
from app.database import Base
import enum

class CastRole(enum.Enum):
    cast = "cast"
    director = "director"
    crew = "crew"

class MovieCastModel(Base):
    __tablename__ = "movie_cast"
    
    movie_cast_id = Column(BigInteger, primary_key=True, autoincrement=True)
    movie_id = Column(BigInteger, ForeignKey('movies.movie_id'), nullable=False)
    actor_id = Column(BigInteger, ForeignKey('person.person_id'), nullable=False)
    character_name = Column(String(255), nullable=True)
    role = Column(Enum(CastRole), default=CastRole.cast)
    
    def __repr__(self):
        return f"<MovieCastModel(movie_id={self.movie_id}, actor_id={self.actor_id})>"
