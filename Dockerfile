# Python 버전을 기반으로 이미지 생성
FROM python:3.13.5-slim

# 파이썬이 로그를 즉시 출력하도록 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 컨테이너 내부의 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 파일을 먼저 복사하여 라이브러리 설치 (캐시 활용)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 현재 폴더(backend)의 모든 소스 코드를 작업 디렉토리로 복사
COPY . /app/
