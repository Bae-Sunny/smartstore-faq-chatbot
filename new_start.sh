#!/bin/sh

echo "ChromaDB가 준비될 때까지 기다리는 중..."
# 'chromadb'는 docker-compose.yml에 정의된 서비스 이름
# 8000은 chromadb 컨테이너의 내부 포트
until nc -z chromadb 8000; do
  printf '.'
  sleep 1
done
echo "ChromaDB 준비 완료!"

# populate_chroma.py 스크립트 실행 (멱등성 있게 수정했으므로 안전)
echo "ChromaDB 데이터 확인 및 로드 중..."
python populate_chroma.py

# Django 개발 서버 시작
echo "Django 개발 서버 시작 중..."
python manage.py runserver 0.0.0.0:8000