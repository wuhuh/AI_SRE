FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY payment-service ./payment-service
WORKDIR /app/payment-service
EXPOSE 8001 8004
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]