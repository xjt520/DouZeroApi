# DouZero API Dockerfile
FROM python:3.9-slim

LABEL maintainer="DouZero API"
LABEL description="DouZero Card Game AI API Service"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements_api.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements_api.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY douzero/ ./douzero/
COPY api/ ./api/
COPY api_server.py .
COPY config.yaml .

# 复制模型文件 (支持 ADP, WP, SL 等模式切换)
COPY baselines/ ./baselines/

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["python", "api_server.py"]
