# 使用Python官方镜像作为基础
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建目录并设置权限（保留root用户运行）
RUN mkdir -p /app/data /app/logs /app/instance && chmod -R 777 /app/data /app/logs /app/instance

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 运行应用，使用新的application对象
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:application"]