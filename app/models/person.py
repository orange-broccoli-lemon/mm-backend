# app/models/person.py

from sqlalchemy import Column, BigInteger, String, Text
from app.database import Base

class PersonModel(Base):
    __tablename__ = "person"
    
    person_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    profile_image_url = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<PersonModel(id={self.person_id}, name='{self.name}')>"
