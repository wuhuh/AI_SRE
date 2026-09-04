FROM python:3.11-slim

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app app && mkdir -p /tmp/checkpoints /tmp/idempotency
COPY agent-runtime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent-runtime/app ./app
COPY knowledge-base /knowledge-base
RUN chown -R app:app /app /knowledge-base /tmp/checkpoints /tmp/idempotency
ENV PYTHONPATH=/app
USER app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]