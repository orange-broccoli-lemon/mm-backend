# app/models/movie_cast.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class MovieCastModel(Base):
    __tablename__ = "movie_casts"
    
    movie_id = Column(Integer, ForeignKey('movies.movie_id'), primary_key=True)
    person_id = Column(Integer, ForeignKey('persons.person_id'), primary_key=True)
    character_name = Column(String(255), nullable=True)  # 배역명
    job = Column(String(100), nullable=True)  # Director, Actor 등
    department = Column(String(100), nullable=True)  # Directing, Acting 등
    cast_order = Column(Integer, nullable=True)  # 출연 순서 (주연일수록 낮은 숫자)
    is_main_cast = Column(Boolean, default=False)  # 주연 여부
    
    def __repr__(self):
        return f"<MovieCastModel(movie_id={self.movie_id}, person_id={self.person_id}, job='{self.job}')>"
