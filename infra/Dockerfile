# 공시지기 이미지 — 빌드: docker build -f infra/Dockerfile -t gonsijigi .
FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data ./data
EXPOSE 8000
# 수업 교훈: CMD 포트가 코드 내 설정보다 우선 · 코드 수정 후 재빌드 필수
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
