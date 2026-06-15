# 使用 Docker 部署 Ollama + Qwen3:0.6B

## 📁 项目结构

```
linux_homework8/
├── Dockerfile                 # 构建带模型自动拉取的 Ollama 镜像
├── docker-compose.yml         # 一键编排启动
├── scripts/
│   └── entrypoint.sh          # 容器启动脚本（自动拉取模型）
├── mcp-server/                # 【选做】MCP 服务
│   ├── Dockerfile
│   └── server.py
└── README.md
```

---

## 一、部署 Ollama + Qwen3:0.6B

### 前提条件

- 已安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 已安装 [Docker Compose](https://docs.docker.com/compose/install/)（Docker Desktop 自带）

### 1. 构建并启动

```bash
# 在项目目录下执行
cd C:\Users\32102\Desktop\python\linux_homework\linux_homework8

# 构建镜像并启动容器
docker compose up -d --build
```

首次启动会自动下载 qwen3:0.6b 模型（约 0.4GB），模型数据保存在 Docker Volume 中，重启容器无需重新下载。

### 2. 查看运行状态

```bash
# 查看容器日志
docker compose logs -f

# 查看容器状态
docker compose ps
```

看到 `Ollama 服务运行中 → http://0.0.0.0:11434` 即表示启动成功。

### 3. 测试 API

```bash
# 健康检查
curl http://localhost:11434/api/tags

# 调用模型进行对话
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:0.6b",
  "messages": [
    {"role": "user", "content": "你好，请用一句话介绍你自己"}
  ],
  "stream": false
}'
```

### 4. 常用命令

```bash
docker compose down          # 停止并删除容器
docker compose up -d         # 以后台模式重新启动
docker compose restart       # 重启容器
docker compose logs -f       # 实时查看日志
```

### 5. GPU 加速（可选）

如果你有 NVIDIA 显卡，安装 [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 后，取消 `docker-compose.yml` 中 GPU 相关注释，重启即可。

---

## 二、Cherry Studio 接入配置

1. **打开 Cherry Studio** → 点击左下角 **设置 ⚙️**

2. **添加模型提供商**：
   - 选择 **Ollama**
   - API 地址填写：`http://127.0.0.1:11434`
   - 点击 **启用** / **刷新模型列表**
   - 应该能看到 `qwen3:0.6b` 出现在列表中

3. **开始对话**：
   - 新建对话
   - 在顶部模型选择器中切换到 `qwen3:0.6b`
   - 即可开始对话！

> 📌 提示：11434 是 Ollama 的默认端口，无需修改。

---

## 三、选做：部署自己的 MCP 服务

### 1. 构建并启动 MCP 服务

```bash
cd mcp-server

# 构建镜像
docker build -t my-mcp-server .

# 运行容器（映射到 8080 端口）
docker run -d --name mcp-server -p 8080:8080 my-mcp-server
```

### 2. 测试 MCP 工具

```bash
# 测试计算器
curl "http://localhost:8080/sse"

# 或者通过 MCP Inspector 测试
npx @anthropic-ai/mcp-inspector http://localhost:8080/sse
```

### 3. 在 Cherry Studio 中接入 MCP 服务

1. 打开 Cherry Studio 设置 → **MCP 服务**
2. 添加 MCP 服务器：
   - 名称：`MyTools`
   - 传输类型：`SSE (Server-Sent Events)`
   - URL：`http://127.0.0.1:8080/sse`
3. 启用后，Cherry Studio 即可调用 MCP 工具（计算器、时间查询、文本处理）

### 提供的 MCP 工具

| 工具 | 功能 | 示例 |
|------|------|------|
| `calculator` | 安全计算表达式 | `"2+3*4"` → `"14"` |
| `current_time` | 获取当前时间 | `""` → `"2026-06-15 14:30:00"` |
| `text_tool` | 文本反转/大小写/长度 | `"hello", "reverse"` → `"olleh"` |

---

## 四、一键全栈启动（包含 MCP 服务）

可以将 MCP 服务也加入 `docker-compose.yml`（在项目根目录的 `docker-compose.yml` 中添加）：

```yaml
  mcp-server:
    build: ./mcp-server
    container_name: mcp-server
    ports:
      - "8080:8080"
    restart: unless-stopped
```

然后：

```bash
docker compose up -d --build
```

两个服务将同时启动：
- **Ollama API** → `http://localhost:11434`
- **MCP Server** → `http://localhost:8080/sse`

---

## 🧹 清理

```bash
# 停止所有服务
docker compose down

# 删除模型数据卷（可选，会清除已下载的模型）
docker volume rm linux_homework8_ollama-data
```
