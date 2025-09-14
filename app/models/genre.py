# app/models/genre.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class GenreModel(Base):
    __tablename__ = "genres"
    
    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    def __repr__(self):
        return f"<GenreModel(id={self.genre_id}, name='{self.name}')>"
