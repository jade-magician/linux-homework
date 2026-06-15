FROM ollama/ollama:latest

# 安装下载工具（用于从国内镜像下载 GGUF 模型）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 复制启动脚本
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露 Ollama API 端口
EXPOSE 11434

# 设置环境变量
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODEL=qwen3:0.6b

# GGUF 模型下载配置（使用国内镜像）
ENV GGUF_DOWNLOAD_URL=https://hf-mirror.com/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf
ENV GGUF_FILENAME=Qwen3-0.6B-Q8_0.gguf

ENTRYPOINT ["/entrypoint.sh"]
