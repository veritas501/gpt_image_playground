# image2-gen

内网图片生成代理项目。

这个仓库不是“一个前端项目 + 一个后端项目”的松散拼接，而是一个完整的单体交付物：

- `frontend/`：内部专用 Web 客户端，负责交互、任务恢复、图片展示、遮罩编辑
- `backend/`：FastAPI 代理服务，负责鉴权、任务执行、上游调用、图片落盘、静态托管
- `data/`：运行时图片目录，保存输入图、遮罩图、输出图
- `docs/`：项目级文档，统一说明架构、开发、部署与 API

## 项目定位

与原始“浏览器直连 OpenAI/兼容接口”的方案不同，当前架构是：

```text
Browser SPA -> FastAPI Backend -> Internal Upstream Image API
```

这样做的目标是：

- 敏感配置只留在后端 `config.toml`
- 前端只保存 `X-Access-Token` 和本地任务 `request_id`
- 后端统一持久化任务与图片，任务元数据存放在 SQLite
- 生产环境单端口交付，前后端一体部署

## 当前能力

- 文生图
- 参考图编辑
- 遮罩编辑
- 本地保存任务 ID，并按 ID 拉取详情
- 后端持久化原图与任务元数据
- 生产环境由 FastAPI 托管前端静态文件
- 固定 `X-Access-Token` 鉴权
- `config.toml` 管理上游地址、模型、口令等敏感配置

## 快速开始

### 1. 前端依赖

```bash
cd "./frontend"
bun install
```

### 2. 后端依赖

```bash
cd "./backend"
uv venv
uv sync
cp "./config.example.toml" "./config.toml"
```

### 3. 开发模式启动

终端 1：

```bash
cd "./backend"
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

终端 2：

```bash
cd "./frontend"
bun run dev --host 0.0.0.0 --port 5173
```

### 4. 生产模式启动

```bash
cd "./frontend"
bun run build

cd "../backend"
uv sync
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

默认情况下，后端会从 `frontend/dist` 托管静态资源。

## 常用命令

### 前端

```bash
cd "./frontend"
bun run test
bun run build
```

### 后端

```bash
cd "./backend"
uv sync --extra test
uv run pytest
```

## 目录结构

```text
image2-gen/
├── frontend/              # React/Vite 客户端
├── backend/               # FastAPI 服务
├── data/                  # 运行时图片文件
├── docs/                  # 项目级文档
├── AGENTS.md              # 仓库协作约束
└── README.md              # 项目入口
```

## 文档索引

- [文档总览](./docs/README.md)
- [架构说明](./docs/architecture.md)
- [开发指南](./docs/development.md)
- [生产部署](./docs/production.md)
- [后端 API](./docs/api.md)
- [实现方案与设计权威文档](./docs/PLAN.md)

## 权威边界

- 架构与接口设计以 [docs/PLAN.md](./docs/PLAN.md) 为准
- 项目级运行与部署说明以 `docs/` 为准
- `frontend/docs/` 下的内容主要来自参考前端项目，保留为前端侧历史资料，不作为当前架构权威说明
