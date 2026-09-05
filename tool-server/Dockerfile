FROM python:3.11-slim

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app app
COPY requirements.txt .
# 网络受限环境：默认清华 PyPI 镜像，可用 --build-arg 覆盖
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN chown -R app:app /app
USER app
EXPOSE 8081
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]