# app/models/movie.py

from sqlalchemy import Column, Integer, String, Text, Date, DECIMAL, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class MovieModel(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True)
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
    updated_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    concise_review = Column(Text, nullable=True, comment="AI 분석 리뷰 요약")
    concise_review_date = Column(DateTime, nullable=True, comment="리뷰 분석 일시")

    def __repr__(self):
        return f"<MovieModel(movie_id={self.movie_id}, title='{self.title}')>"
