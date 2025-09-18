# app/services/scheduler_service.py

import asyncio
from datetime import datetime, timedelta
from typing import List
from app.services.user_service import UserService
from app.services.comment_service import CommentService
from app.ai import profile_reviewbot


class SchedulerService:

    def __init__(self):
        pass

    async def daily_profile_analysis(self):
        """매일 오전 6시 사용자 프로필 분석"""
        print(f"프로필 분석 스케줄러 시작: {datetime.now()}")

        user_service = UserService()
        comment_service = CommentService()

        try:
            # 1. 모든 활성 사용자 조회
            users = await user_service.get_all_active_users()
            print(f"분석 대상 사용자 수: {len(users)}")

            analysis_count = 0

            for user in users:
                try:
                    # 2. 사용자의 댓글 조회
                    comments = await comment_service.get_user_all_comments_text(user.user_id)

                    # 3. 댓글이 5개 이상일 때만 분석
                    if len(comments) >= 5:
                        print(
                            f"사용자 {user.name}({user.user_id}) 프로필 분석 시작 - 댓글 {len(comments)}개"
                        )

                        # 4. AI 프로필 분석 수행
                        profile_analysis = await profile_reviewbot(user.name, comments)

                        # 5. 결과를 DB에 저장
                        success = await user_service.update_user_profile_review(
                            user.user_id, profile_analysis
                        )

                        if success:
                            analysis_count += 1
                            print(f"사용자 {user.name} 프로필 분석 완료")
                        else:
                            print(f"사용자 {user.name} 프로필 저장 실패")
                    else:
                        print(f"사용자 {user.name}({user.user_id}) - 댓글 부족 ({len(comments)}개)")

                    # 6. API 부하 방지를 위한 딜레이
                    await asyncio.sleep(2)

                except Exception as user_error:
                    print(f"사용자 {user.name}({user.user_id}) 분석 실패: {str(user_error)}")
                    continue

            print(f"프로필 분석 완료: {analysis_count}명 성공")

        except Exception as e:
            print(f"프로필 분석 스케줄러 오류: {str(e)}")
        finally:
            # 리소스 정리
            user_service.__del__()
            comment_service.__del__()

    async def run_scheduler(self):
        """스케줄러 실행"""
        while True:
            try:
                now = datetime.now()
                target_time = now.replace(hour=6, minute=0, second=0, microsecond=0)

                # 오늘 6시가 이미 지났으면 내일 6시로 설정
                if now >= target_time:
                    target_time += timedelta(days=1)

                # 다음 실행까지 대기
                wait_seconds = (target_time - now).total_seconds()
                print(f"다음 프로필 분석 예정: {target_time}")

                await asyncio.sleep(wait_seconds)

                # 프로필 분석 실행
                await self.daily_profile_analysis()

            except Exception as e:
                print(f"스케줄러 오류: {str(e)}")
                # 오류 발생 시 1시간 후 재시도
                await asyncio.sleep(3600)
