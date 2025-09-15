# app/models/person.py

from sqlalchemy import Column, Integer, String, Text, Date, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class PersonModel(Base):
    __tablename__ = "persons"
    
    person_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)
    biography = Column(Text, nullable=True)
    birthday = Column(Date, nullable=True)
    deathday = Column(Date, nullable=True)
    place_of_birth = Column(String(255), nullable=True)
    profile_image_url = Column(Text, nullable=True)
    gender = Column(Integer, nullable=True)
    known_for_department = Column(String(100), nullable=True)
    popularity = Column(Integer, default=0)
    is_adult = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<PersonModel(id={self.person_id}, name='{self.name}')>"
