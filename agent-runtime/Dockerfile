FROM python:3.11-slim

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app app && mkdir -p /tmp/checkpoints /tmp/idempotency
COPY agent-runtime/requirements.txt .
# 网络受限环境：默认清华 PyPI 镜像，可用 --build-arg 覆盖
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir -r requirements.txt
COPY agent-runtime/app ./app
COPY knowledge-base /knowledge-base
RUN chown -R app:app /app /knowledge-base /tmp/checkpoints /tmp/idempotency
ENV PYTHONPATH=/app
USER app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]