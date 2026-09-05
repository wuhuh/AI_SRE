FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
# 网络受限环境：默认清华 PyPI 镜像，可用 --build-arg 覆盖
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY payment-service ./payment-service
WORKDIR /app/payment-service
EXPOSE 8001 8004
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]