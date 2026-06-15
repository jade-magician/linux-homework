#!/bin/bash
set -e

echo "=========================================="
echo "  Ollama + Qwen3:0.6B 容器启动中..."
echo "=========================================="

# 在后台启动 Ollama 服务
ollama serve &
OLLAMA_PID=$!

# 等待服务就绪
echo "正在等待 Ollama 服务启动..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama 服务已就绪！"
        break
    fi
    sleep 1
done

# 检查模型是否已存在
if ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL}"; then
    echo "模型 ${OLLAMA_MODEL} 已存在，跳过下载。"
else
    MODEL_DIR="/root/.ollama/models"
    GGUF_PATH="${MODEL_DIR}/${GGUF_FILENAME}"

    # 如果 GGUF 文件不存在则下载（使用国内镜像）
    if [ ! -f "${GGUF_PATH}" ]; then
        echo "=========================================="
        echo "从国内镜像下载 GGUF 模型文件..."
        echo "下载地址: ${GGUF_DOWNLOAD_URL}"
        echo "文件大小: ~660MB, 请耐心等待..."
        echo "=========================================="
        mkdir -p "${MODEL_DIR}"
        curl -L --progress-bar -o "${GGUF_PATH}" "${GGUF_DOWNLOAD_URL}"
        echo ""
        echo "GGUF 下载完成！"
    else
        echo "GGUF 文件已存在，跳过下载。"
    fi

    # 创建 Ollama Modelfile 并导入模型
    echo "=========================================="
    echo "正在将 GGUF 模型导入 Ollama..."
    echo "=========================================="

    MODELFIRE="/tmp/Modelfile"
    cat > "${MODELFIRE}" << MODELF
FROM ${GGUF_PATH}
PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
MODELF

    ollama create "${OLLAMA_MODEL}" -f "${MODELFIRE}"
    rm -f "${MODELFIRE}"

    echo "模型导入完成！"
fi

echo ""
echo "=========================================="
echo "  Ollama 服务运行中 → http://0.0.0.0:11434"
echo "  模型: ${OLLAMA_MODEL}"
echo "=========================================="

# 将 Ollama 服务切回前台
wait $OLLAMA_PID
