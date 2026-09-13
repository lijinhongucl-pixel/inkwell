# Docker 多阶段构建实战指南

## 为什么需要多阶段构建

Docker 镜像太大是个老问题。一个 Python 项目如果用单阶段构建，镜像动辄 800MB 以上。多阶段构建能把最终镜像压到 120MB 左右，体积降 80% 以上。

==核心思路很简单：编译阶段用完整镜像，运行阶段只拷贝产物。==

## 对比：单阶段 vs 多阶段

| 方式 | 镜像大小 | 构建时间 | 安全性 |
|------|---------|---------|-------|
| 单阶段 | 800MB+ | 基准 | 包含编译器等工具 |
| 多阶段 | ~120MB | 略增 | 只含运行时 |

## 多阶段构建模板

### Stage 1: Builder

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install .

COPY src/ src/
RUN /opt/venv/bin/pip install .
```

### Stage 2: Runtime

```dockerfile
FROM python:3.12-slim

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1001 appuser
USER appuser

ENTRYPOINT ["dumb-init", "--"]
CMD ["inkwell", "--help"]
```

## 关键优化点

### 1. 用 slim 而非 full

`python:3.12-slim` 比 `python:3.12` 少约 400MB。大多数 Python 项目不需要 full 镜像里的编译工具链。

### 2. 非 root 运行

```dockerfile
RUN useradd -m -u 1001 appuser
USER appuser
```

安全性最佳实践。即使容器内应用被攻破，攻击者也没有 root 权限。

### 3. venv 拷贝而非全局安装

builder 阶段装到 `/opt/venv`，runtime 阶段整目录拷过来。好处是依赖树完整、不污染 runtime 全局环境。

### 4. dumb-init 信号转发

```dockerfile
ENTRYPOINT ["dumb-init", "--"]
```

解决 PID 1 问题的经典方案。没有 init 系统的容器在收到 SIGTERM 时会忽略，导致停止超时。

## 常见坑

### 坑 1: 忘记 WORKDIR 导致 COPY 路径错乱

```dockerfile
# 错误：没设 WORKDIR，COPY 默认放 /
COPY src/ src/

# 正确：先设 WORKDIR
WORKDIR /app
COPY src/ src/
```

### 坑 2: 层缓存破坏

```dockerfile
# 错误：代码一改就重建所有依赖
COPY . .
RUN pip install .

# 正确：先拷依赖文件，再拷代码
COPY pyproject.toml .
RUN pip install .
COPY src/ src/
```

### 坑 3: 最终镜像混入测试依赖

```dockerfile
# builder 阶段可以装 dev 依赖
RUN pip install ".[dev]"

# 但 runtime 阶段只拷 venv，不要装 dev 依赖
# venv 里如果有 dev 依赖，在 builder 最后一步清理：
RUN /opt/venv/bin/pip uninstall -y pytest pytest-cov
```

## 验证镜像大小

```bash
docker images inkwell
# REPOSITORY          TAG       SIZE
# inkwell    latest    123MB
```

如果超过 200MB，检查 builder 阶段是否有多余的工具被拷进了 venv。

## 结论

多阶段构建是 Docker 镜像优化的标准做法。记住三个原则就够了：

1. 编译和运行分阶段
2. 最终镜像只拷产物不拷工具
3. 非 root + init 守护
