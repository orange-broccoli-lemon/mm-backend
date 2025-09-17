# app/models/movie_cast.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class MovieCastModel(Base):
    __tablename__ = "movie_casts"

    movie_id = Column(Integer, ForeignKey("movies.movie_id"), primary_key=True)
    person_id = Column(Integer, ForeignKey("persons.person_id"), primary_key=True)
    character_name = Column(String(255), nullable=True)
    job = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    cast_order = Column(Integer, nullable=True)
    is_main_cast = Column(Boolean, default=False)

    def __repr__(self):
        return f"<MovieCastModel(movie_id={self.movie_id}, person_id={self.person_id}, job='{self.job}')>"
