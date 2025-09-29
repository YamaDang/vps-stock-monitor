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

# 创建数据和日志目录并设置权限
RUN mkdir -p /app/data /app/logs && chmod -R 777 /app/data /app/logs

# 创建非root用户
RUN useradd -m -u 1000 appuser

# 更改应用目录的所有权
RUN chown -R appuser:appuser /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 切换到appuser用户
USER appuser

# 运行应用
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]