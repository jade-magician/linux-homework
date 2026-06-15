FROM python:3.12-slim

WORKDIR /app

# 使用国内 PyPI 镜像安装 MCP SDK
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple mcp

# 复制服务端代码
COPY server.py /app/server.py

EXPOSE 8080

CMD ["python", "/app/server.py"]
