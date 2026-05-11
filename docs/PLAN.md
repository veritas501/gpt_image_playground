# PLAN — image2-gen 前后端改造方案

## 1. 目标

以 `refs/gpt_image_playground` 为基线，保留其全部核心交互能力（文生图、参考图编辑、遮罩编辑、任务列表、详情、历史、参数管理、结果复用等），将架构从"浏览器直连图片 API"改为"前端 → FastAPI 后端 → 内网上游"，实现：

- 刷新页面后任务不丢、继续轮询
- 图片由后端持久化，前端按需查询
- 敏感配置（上游地址、密钥等）收口到后端 `config.toml`
- 前端不再暴露 API Key / Provider 等通用配置面板

---

## 2. 整体架构

```
┌──────────────┐        ┌─────────────────┐        ┌──────────────┐
│  前端 (SPA)   │ ──→    │  FastAPI 后端    │ ──→    │  内网上游     │
│ React + Vite │ ←──    │  (Python)       │ ←──    │  图片 API     │
│ 静态托管      │        │  SQLite + 文件   │        │              │
└──────────────┘        └─────────────────┘        └──────────────┘
     browser                  server                  internal net
```

- **开发期**: Vite dev server (`:5173`) + FastAPI dev server (`:8000`)，CORS/代理分离
- **生产期**: FastAPI 同时提供 API 并托管前端 `dist/` 静态文件，单端口对外

**职责划分**

| 层 | 职责 |
|---|---|
| 前端 | 交互、遮罩编辑器、任务列表/详情/下载、结果复用；每次请求通过 header 携带固定口令 |
| 后端 | 鉴权、任务创建/查询/删除、调用上游 API、图片落盘、图片查询/下载、生产托管前端产物 |
| 存储 | SQLite 管任务元数据与索引；本地文件系统管原始图片 |
| 上游 | 内网图片 API（由后端持固定密钥调用） |

**目录结构**

```
image2-gen/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口，路由注册，生产静态托管
│   │   ├── config.py        # config.toml 解析
│   │   ├── models.py        # SQLAlchemy / ORM 模型
│   │   ├── schemas.py       # Pydantic 请求/响应 schema
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py      # /api/auth/*
│   │   │   ├── tasks.py     # /api/tasks/*
│   │   │   ├── images.py    # /api/images/*
│   │   │   └── app.py       # /api/app/config
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── task_service.py   # 任务业务逻辑
│   │   │   ├── image_service.py  # 图片业务逻辑
│   │   │   └── upstream.py       # 调内网上游 API
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── task_repo.py      # 任务数据访问
│   │   │   └── image_repo.py     # 图片数据访问
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── file_storage.py   # 文件系统读写
│   ├── config.toml
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                  # 从 refs/gpt_image_playground 拷贝并改造
│   ├── src/
│   │   ├── lib/
│   │   │   ├── backendApi.ts      # 新：前后端通信层
│   │   │   └── ...                # 原有文件按需裁剪
│   │   └── ...
│   └── package.json
├── data/                      # 运行时数据（gitignore）
│   ├── app.db
│   └── images/
│       ├── inputs/
│       ├── masks/
│       └── outputs/
└── PLAN.md                    # 本文件
```

---

## 3. 后端 API 设计

### 3.1 鉴权

所有 `/api/*` 接口校验 header：

```
X-Access-Token: <口令>
```

- 口令在 `config.toml` 中配置
- 校验失败统一返回 `403 { "detail": "invalid access token" }`
- 前端保存 token，每次请求带上

### 3.2 任务接口

#### `POST /api/tasks` — 创建任务

请求 `multipart/form-data`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `prompt` | string | 提示词 |
| `mode` | string | `generate` / `edit` |
| `params` | string(JSON) | 生成参数 |
| `input_images` | file[] | 参考图（0-16 张） |
| `mask` | file | 遮罩图（仅 edit 模式） |
| `mask_target_index` | int | 遮罩作用的参考图索引 |
| `n` | int | 生成数量 |
| `size` | string | 尺寸 |
| `quality` | string | 质量 |
| `output_format` | string | 格式 |
| `output_compression` | int | 压缩率 |
| `moderation` | string | 审核等级 |

返回 `201`：

```json
{
  "request_id": "abc123",
  "status": "queued",
  "created_at": "2026-05-11T10:00:00Z"
}
```

#### `GET /api/tasks` — 任务列表

Query 参数：

| 参数 | 说明 |
|---|---|
| `status` | 过滤状态，默认全部 |
| `q` | 搜索 prompt |
| `page` | 页码 |
| `page_size` | 每页数 |

返回：

```json
{
  "tasks": [ ... ],
  "total": 42
}
```

#### `GET /api/tasks/{request_id}` — 任务详情

返回完整任务信息，包括 input_image_ids、mask_image_id、output_image_ids、actual_params、revised_prompt、elapsed、error 等。

#### `POST /api/tasks/{request_id}/retry` — 重试

基于原任务重新创建新任务。

#### `DELETE /api/tasks/{request_id}` — 删除

可选 `?keep_images=true` 保留图片文件。

### 3.3 图片接口

#### `GET /api/images/{image_id}` — 获取图片

返回图片二进制流（`Content-Type: image/*`）。

#### `GET /api/images/{image_id}/download` — 下载

同上，附加 `Content-Disposition: attachment`。

#### `GET /api/images/{image_id}/thumbnail` — 缩略图

返回缩略图流（可选）。后端在存储图片时预生成缩略图，减少列表加载压力。

### 3.4 应用配置接口

#### `GET /api/app/config`

返回前端运行时配置（非敏感）：

```json
{
  "app_name": "Image Gen",
  "default_model": "gpt-image-2",
  "api_mode": "images",
  "supported_sizes": ["1024x1024", ...],
  "default_params": { ... }
}
```

**不返回**：上游地址、密钥、访问口令。

---

## 4. 任务状态机

```
queued ──→ running ──→ succeeded
  │            │
  └──────→ failed ←─────┘
```

| 状态 | 含义 |
|---|---|
| `queued` | 任务已创建，等待执行 |
| `running` | 正在调上游 / 下载结果 |
| `succeeded` | 成功，输出图已落盘 |
| `failed` | 失败，error 字段记录原因 |

可选扩展：`cancelling` → `cancelled`（首版可暂不做）。

---

## 5. 数据模型（SQLite）

### 5.1 tasks 表

```sql
CREATE TABLE tasks (
    id            TEXT PRIMARY KEY,        -- request_id (UUID7 或时间戳+随机)
    prompt        TEXT NOT NULL,
    mode          TEXT NOT NULL,           -- 'generate' | 'edit'
    params_json   TEXT NOT NULL,           -- JSON: 生成参数
    status        TEXT NOT NULL DEFAULT 'queued',
    error         TEXT,
    api_mode      TEXT,                    -- 'images' | 'responses'
    api_model     TEXT,
    elapsed_ms    INTEGER,
    actual_params_json TEXT,               -- 上游实际生效参数
    revised_prompt TEXT,                   -- 上游改写后的 prompt
    raw_response_payload TEXT,             -- 原始响应用于调试
    raw_image_urls TEXT,                   -- JSON array: 原始图片 URL
    created_at    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT
);
```

### 5.2 images 表

```sql
CREATE TABLE images (
    id            TEXT PRIMARY KEY,        -- UUID
    task_id       TEXT NOT NULL,           -- 关联任务
    kind          TEXT NOT NULL,           -- 'input' | 'mask' | 'output'
    file_path     TEXT NOT NULL,           -- 相对路径
    mime_type     TEXT NOT NULL,
    width         INTEGER,
    height        INTEGER,
    thumbnail_path TEXT,                   -- 缩略图相对路径
    created_at    TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

### 5.3 task_images 关联表

```sql
CREATE TABLE task_images (
    task_id     TEXT NOT NULL,
    image_id    TEXT NOT NULL,
    role        TEXT NOT NULL,             -- 'input' | 'mask' | 'output'
    sort_order  INTEGER DEFAULT 0,
    PRIMARY KEY (task_id, image_id, role)
);
```

### 5.4 文件布局

```
data/
├── app.db
└── images/
    ├── inputs/    {image_id}.{ext}
    ├── masks/     {image_id}.{ext}
    ├── outputs/   {image_id}.{ext}
    └── thumbs/    {image_id}.webp
```

---

## 6. config.toml 设计

```toml
[server]
host = "0.0.0.0"
port = 8000

[security]
access_token = "your-fixed-token-here"

[upstream]
base_url = "https://your-internal-api.example.com/v1"
api_key = "sk-xxxxxxxx"
default_model = "gpt-image-2"
timeout_seconds = 120

[app]
app_name = "Image Gen"
api_mode = "images"                          # "images" | "responses"
static_dir = "../frontend/dist"              # 生产静态文件路径

[images]
storage_dir = "data/images"
thumbnail_max_size = 720
thumbnail_quality = 0.9
```

---

## 7. 前端改造要点

### 7.1 新增文件

- `src/lib/backendApi.ts` — 统一的 fetch 封装，携带 `X-Access-Token`，封装所有后端接口

### 7.2 重点改造文件

| 文件 | 改造内容 |
|---|---|
| `src/store.ts` | 任务/图片来源改为后端；去掉 IndexedDB 持久化；去掉 markInterrupted；去掉 fal/custom recovery |
| `src/lib/api.ts` | 替换 callImageApi 为调用 `POST /api/tasks` + 轮询 |
| `src/lib/db.ts` | 可整体移除（或保留为缓存层） |
| `src/types.ts` | Type/TaskRecord 对齐新模型 |
| `src/components/SettingsModal.tsx` | 大幅收口：只保留与生成相关的参数，去掉 provider/key 配置 |
| `src/components/InputBar.tsx` | 文件上传改为直接发给后端 |

### 7.3 可基本复用

- `MaskEditorModal.tsx` — 遮罩编辑 UI
- `TaskCard.tsx` / `TaskGrid.tsx` — 改造后数据驱动层变更，UI 复用
- `DetailModal.tsx` — 详情展示
- `Lightbox.tsx` / `Toast.tsx` — 通用 UI
- `SizePickerModal.tsx` — 尺寸选择
- `lib/size.ts` / `lib/canvasImage.ts` / `lib/mask.ts` — 纯前端逻辑

### 7.4 前端任务/图片数据流（新）

```
用户提交 → POST /api/tasks (multipart) → 得到 request_id
         → 轮询 GET /api/tasks/{request_id} → 直到 status ∈ {succeeded, failed}
         → 前端展示结果：<img src="/api/images/{image_id}" />
         → 遮罩/编辑 → 图片仍先发给后端存储
         → 重试 → POST /api/tasks/{request_id}/retry
         → 删除 → DELETE /api/tasks/{request_id}
```

与原有流程相比：
- 不再调用 OpenAI/fal 兼容接口
- 不再把图片 as data URL 在 IndexedDB 和内存间搬运
- 任务和图片的真实来源永远是后端

---

## 8. 实施计划

### 阶段 1：后端骨架

- [ ] 初始化 `backend/` Python 项目（`pyproject.toml` / `requirements.txt`）
- [ ] 实现 `config.py`（读取 `config.toml`）
- [ ] 搭建 FastAPI `main.py`（包含 access token 中间件）
- [ ] SQLite 建表与 ORM 模型
- [ ] 文件存储工具函数
- [ ] 验证：FastAPI 启动、config 可读、数据库可创建

### 阶段 2：后端核心 API

- [ ] `POST /api/tasks` — 创建任务，接收 multipart
- [ ] `GET /api/tasks` — 任务列表
- [ ] `GET /api/tasks/{id}` — 任务详情
- [ ] 后台任务执行器（AsyncIO 后台任务或线程池）
- [ ] 上游 API 调用模块（`images/generations` + `images/edits` + `responses`）
- [ ] 图片落盘与数据库记录
- [ ] `GET /api/images/{id}` / thumbnail / download
- [ ] 验证：curl 测试创建任务 → 轮询到完成 → 查看图片

### 阶段 3：后端完善

- [ ] `POST /api/tasks/{id}/retry`
- [ ] `DELETE /api/tasks/{id}`
- [ ] `GET /api/app/config`
- [ ] 生产态静态文件托管
- [ ] 异常处理与错误信息完善
- [ ] 验证：完整流程集成测试

### 阶段 4：前端拷贝与基础改造

- [ ] 拷贝参考项目到 `frontend/`
- [ ] 新增 `backendApi.ts`
- [ ] 修改 `types.ts` 对齐新模型
- [ ] 去掉 provider 配置面板
- [ ] 接入 access token（UI 上增加 token 输入/保存）
- [ ] 验证：前端可连接后端、鉴权通过

### 阶段 5：前端任务流程对接

- [ ] 改造 `store.ts`：去掉 IndexedDB，接入后端任务/图片接口
- [ ] 改造提交流程：`POST /api/tasks` + 轮询
- [ ] 改造历史列表：数据源改为后端
- [ ] 改造详情页：从后端查询
- [ ] 改造图片展示：后端图片 URL
- [ ] 改造重试/删除/编辑输出
- [ ] 验证：完整交互可用

### 阶段 6：打磨与收尾

- [ ] 遮罩编辑器与后端对接
- [ ] `responses` 模式支持
- [ ] 参数对比（actual_params）
- [ ] revised_prompt 展示
- [ ] 缩略图预生成与加载优化
- [ ] 错误详情展示
- [ ] 全流程测试与回归

---

## 9. 设计决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| 架构方案 | A（前端最小侵入） | 用户要求直接拷贝参考项目并保留全部能力 |
| 接口风格 | 前端专用任务接口 | 不再伪装 OpenAI 兼容，简化前后端 |
| 后端框架 | FastAPI | 用户指定 |
| 存储 | SQLite + 文件系统 | 单机部署，无外部依赖 |
| 鉴权 | 固定 token + header | 用户偏好简单保护 |
| 部署 | dev 分离 / prod 合并 | 用户指定方案 3 |
| 任务执行 | 异步后台执行 | 支持刷新恢复 |
| 图片策略 | 后端持久化 | 支持刷新恢复与长期保存 |
| 旧数据迁移 | 不需要 | 这是新项目 |
| 清理策略 | 默认不清理 | 用户指定 |
