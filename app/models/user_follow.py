# app/models/user_follow.py

from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class UserFollowModel(Base):
    __tablename__ = "user_follows"

    follower_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True
    )  # 팔로우하는 사람
    following_id = Column(
        BigInteger, ForeignKey("users.user_id"), primary_key=True
    )  # 팔로우 당하는 사람
    created_at = Column(DateTime, default=func.current_timestamp())

    # 복합 기본키로 중복 팔로우 방지
    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="unique_follow"),)

    def __repr__(self):
        return (
            f"<UserFollowModel(follower_id={self.follower_id}, following_id={self.following_id})>"
        )
