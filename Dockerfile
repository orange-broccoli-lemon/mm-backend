# Python 버전을 기반으로 이미지 생성
FROM python:3.13.5-slim

# 파이썬이 로그를 즉시 출력하도록 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 컨테이너 내부의 작업 디렉토리 설정
WORKDIR /app

# 가상환경 생성 경로 지정
ENV VENV_PATH="/opt/venv"

# 가상환경 생성
RUN python -m venv $VENV_PATH
 --
# 가상환경 내 pip 최신화
RUN $VENV_PATH/bin/pip install --upgrade pip

# requirements.txt 파일을 먼저 복사하여 라이브러리 설치 (캐시 활용)
COPY requirements.txt /app/

# 의존성 가상환경에 설치
RUN $VENV_PATH/bin/pip install --no-cache-dir -r requirements.txt

# 현재 폴더(backend)의 모든 소스 코드를 작업 디렉토리로 복사
COPY . /app/

# 가상환경의 bin 디렉토리를 PATH에 추가하여 python, pip 등을 기본으로 사용
ENV PATH="$VENV_PATH/bin:$PATH"

# 컨테이너 실행 시 기본 명령어 (필요에 따라 수정)
CMD ["python", "main.py"]
