FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PERSONA0_CONFIG_ENV=prod \
    PERSONA0_CONFIG_PROFILE=prod

WORKDIR /app

RUN addgroup --system persona0 && adduser --system --ingroup persona0 persona0

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R persona0:persona0 /app
USER persona0

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -m src.runtime.healthcheck --mode readiness || exit 1

CMD ["python", "-m", "src.runtime.scheduler"]
