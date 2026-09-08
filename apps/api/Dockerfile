FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY apps/api /app
COPY skills /skills
COPY automations /automations
ENV PYTHONPATH=/app
ENV SKILLS_PATH=/skills
ENV AUTOMATIONS_PATH=/automations
ENV STORAGE_PATH=/data/storage
ENV DATABASE_URL=sqlite:////data/docflow.db
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --retries=5 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
