FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PERSONA0_CONFIG_PROFILE=dev

WORKDIR /app

RUN addgroup --system persona0 && adduser --system --ingroup persona0 persona0

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R persona0:persona0 /app
USER persona0

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -m src.runtime.healthcheck --mode readiness || exit 1

# Default: runs with mock LLM provider (dev profile).
# For production with a real LLM provider, override at run time:
#   docker run -e PERSONA0_CONFIG_PROFILE=prod \
#              -e PERSONA0__LLM_ADAPTER__API_KEY=sk-... \
#              persona0
CMD ["python", "-m", "src.runtime.scheduler"]
