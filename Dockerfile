# ============================================================
# Inkwell Dockerfile —— 多阶段构建
# 目标：最终镜像只含运行时必需文件，不含编译器 / 缓存 / 测试依赖
# ============================================================

# ---------- Stage 1: builder ----------
# 依赖（Pillow）在 PyPI 有 manylinux wheel，无需装编译器
FROM python:3.13-slim AS builder

# 设置环境，避免 .pyc 和缓冲，减少体积
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 先单独装依赖（利用 Docker 层缓存：代码变了不重装依赖）
COPY pyproject.toml ./
COPY src/ ./src/

# 用 venv 隔离，最终只拷 venv 到运行镜像
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir .

# ---------- Stage 2: runtime ----------
# 纯运行时，不装编译工具，镜像最小化
FROM python:3.13-slim AS runtime

# 安全：用非 root 用户运行
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# 装 dumb-init 做信号转发（避免僵尸进程），不装其他多余包
# 如果不需要 dumb-init 可以删掉这层，进一步缩小
RUN apt-get update \
    && apt-get install -y --no-install-recommends dumb-init \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 拷 venv（已编译好的依赖）
COPY --from=builder /opt/venv /opt/venv

# 建非 root 用户
RUN useradd -m -u 1001 -s /bin/sh appuser \
    && mkdir -p /app/output \
    && chown -R appuser:appuser /app

USER appuser
WORKDIR /app

# 暴露产出卷（包本体（含 screenshot.js / py.typed）已随 venv 安装）
VOLUME ["/app/output"]

ENTRYPOINT ["dumb-init", "--", "inkwell"]
CMD ["--help"]
