# GenomeLens 开发环境镜像（0.9.20）
#
# 该镜像提供完整的 GenomeLens 开发依赖：
#   - conda Python 3.12（genomelens 环境）
#   - platform 与 engines/jcvi 的 editable install
#   - Node.js 20 + pnpm（GUI 前端构建）
#   - Rust 工具链（Tauri 侧构建）
#
# 注意：镜像不捆绑 BLAST+ / ImageMagick 等外部二进制工具链；
# 真实共线性分析时请在容器内或宿主机额外配置。

FROM condaforge/miniforge:latest

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/root/.cargo/bin:${PATH}"

# 安装基础构建工具与 Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && corepack enable \
    && corepack prepare pnpm@9 --activate \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 Rust（Tauri 需要）
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

WORKDIR /workspace

# 先复制依赖描述文件以利用层缓存
COPY platform/environment.yml /workspace/platform/environment.yml
COPY platform/pyproject.toml /workspace/platform/pyproject.toml
COPY engines/jcvi/pyproject.toml /workspace/engines/jcvi/pyproject.toml

# 创建 conda 环境并安装 platform editable
RUN conda env create -f /workspace/platform/environment.yml \
    && conda clean -afy

# 复制完整源码后再安装 engine editable（engine 依赖完整源码）
COPY . /workspace/

SHELL ["conda", "run", "-n", "genomelens", "/bin/bash", "-c"]
RUN pip install -e /workspace/engines/jcvi

# 烟测：验证版本号与关键导入
RUN python -c "import genomelens; print('genomelens', genomelens.__version__)" \
    && python -c "import jcvi_genomelens; print('jcvi_genomelens', jcvi_genomelens.__version__)"

# GUI 开发端口（Vite dev server）
EXPOSE 1420

CMD ["conda", "run", "-n", "genomelens", "/bin/bash"]
