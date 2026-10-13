# ---- Container image for the Flask app (runs on Amazon ECS Fargate) ----

# Base image from Amazon ECR Public (avoids Docker Hub rate limits)
FROM public.ecr.aws/docker/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# Install dependencies first so Docker can cache this layer
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Security: never run the app as root
RUN useradd --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')" || exit 1

# gunicorn = production web server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app.main:app"]
