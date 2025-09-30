# 가상환경 실행
venv:
	@source .venv/bin/activate

# FastAPI 서버 실행
run:
	@uvicorn app.main:app --reload

# 테스트 실행
test:
	@pytest -v

# 코드 포맷팅
format:
	@black src
	@isort src

# 도커 빌드
docker-build:
	@docker build -t pitterpetter-ai .

# 도커 실행
docker-run:
	@docker run -p 8000:8000 pitterpetter-ai
