# app/services/user_service.py

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import UserModel
from app.schemas.user import User, UserCreateEmail, UserCreateGoogle, UserLoginEmail, UserLoginGoogle
from app.database import get_db
from app.core.auth import get_password_hash, verify_password

class UserService:
    
    def __init__(self):
        self.db: Session = next(get_db())
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                return User.from_orm(user_model)
            return None
            
        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
    
    async def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.google_id == google_id)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model:
                return User.from_orm(user_model)
            return None
            
        except Exception as e:
            raise Exception(f"사용자 조회 실패: {str(e)}")
    
    async def create_user_email(self, user_data: UserCreateEmail) -> User:
        try:
            # 이메일 중복 체크
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise Exception("이미 등록된 이메일입니다")
            
            # 비밀번호 해시화
            hashed_password = get_password_hash(user_data.password)
            
            # 사용자 생성 (이메일 방식)
            user_model = UserModel(
                google_id=None,
                email=user_data.email,
                password_hash=hashed_password,
                name=user_data.name,
                profile_image_url=user_data.profile_image_url
            )
            
            self.db.add(user_model)
            self.db.commit()
            self.db.refresh(user_model)
            
            return User.from_orm(user_model)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"이메일 회원가입 실패: {str(e)}")
    
    async def create_user_google(self, user_data: UserCreateGoogle) -> User:
        try:
            # 이메일 중복 체크
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise Exception("이미 등록된 이메일입니다")
            
            # Google ID 중복 체크
            existing_google_user = await self.get_user_by_google_id(user_data.google_id)
            if existing_google_user:
                raise Exception("이미 등록된 Google 계정입니다")
            
            # 사용자 생성 (구글 방식)
            user_model = UserModel(
                google_id=user_data.google_id,
                email=user_data.email,
                password_hash=None,  # Google 로그인은 비밀번호 없음
                name=user_data.name,
                profile_image_url=user_data.profile_image_url
            )
            
            self.db.add(user_model)
            self.db.commit()
            self.db.refresh(user_model)
            
            return User.from_orm(user_model)
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Google 회원가입 실패: {str(e)}")
    
    async def authenticate_user_email(self, email: str, password: str) -> Optional[User]:
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = self.db.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            # Google 계정인 경우 이메일 로그인 불가
            if user_model.google_id and not user_model.password_hash:
                return None
            
            # 비밀번호 확인
            if not verify_password(password, user_model.password_hash):
                return None
            
            # 마지막 로그인 시간 업데이트
            from datetime import datetime
            user_model.last_login = datetime.utcnow()
            self.db.commit()
            
            return User.from_orm(user_model)
            
        except Exception as e:
            raise Exception(f"이메일 로그인 실패: {str(e)}")
    
    async def authenticate_user_google(self, email: str, google_id: str) -> Optional[User]:
        try:
            # Google ID로 사용자 찾기
            user = await self.get_user_by_google_id(google_id)
            if user and user.email == email:
                # 마지막 로그인 시간 업데이트
                stmt = select(UserModel).where(UserModel.google_id == google_id)
                result = self.db.execute(stmt)
                user_model = result.scalar_one_or_none()
                
                if user_model:
                    from datetime import datetime
                    user_model.last_login = datetime.utcnow()
                    self.db.commit()
                
                return user
            return None
            
        except Exception as e:
            raise Exception(f"Google 로그인 실패: {str(e)}")
    
    async def check_email_exists(self, email: str) -> bool:
        user = await self.get_user_by_email(email)
        return user is not None
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
