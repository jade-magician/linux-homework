# 24376146 李元弋 Linux操作系统与数据库作业

## homework9 — 华强卖瓜 · 买瓜宇宙

基于FastAPI + PostgreSQL的B站买瓜宇宙文字冒险游戏。

### 快速开始（推荐Docker）

```bash
git clone https://github.com/jade-magician/linux-homework.git
cd linux-homework/linux_homework9
docker compose up -d
# 浏览器打开 http://localhost:8000
```

### 本地运行（SQLite，无需Docker）

```bash
cd linux-homework/linux_homework9/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000
```

### 技术栈

- **后端**: Python 3.12 + FastAPI + SQLAlchemy (async)
- **数据库**: PostgreSQL 16 (生产) / SQLite (开发)
- **容器化**: Docker + Docker Compose
- **前端**: 原生 HTML/CSS/JS，打字机效果，Steam风格成就弹窗

### 游戏内容

- 22个主题 × 5种变体 = 110套独立文案
- 25项跨游戏持久化成就
- 过渡动画 + 剧情音频
- 存档/读档/排行榜

### 快捷键

| 键 | 功能 |
|----|------|
| 1/2/3 | 选择对应选项 |
| 回车 | 继续下一天 |
| Esc | 关闭弹窗 |
