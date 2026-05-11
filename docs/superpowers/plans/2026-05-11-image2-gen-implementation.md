# image2-gen 实施计划

## 背景

目标是按 [docs/PLAN.md](/home/veritas/works/image2-gen/docs/PLAN.md) 完成 `image2-gen` 的前后端实现：前端改成内部专用客户端，后端用 FastAPI 代理内网上游，任务与图片以后端为真相源。

## 约束

- 后端技术栈固定为 `Python + FastAPI`
- 前端只暴露 `X-Access-Token`
- 敏感配置统一收口到 `backend/config.toml`
- 存储固定为 `SQLite + 本地文件系统`
- 默认不清理任务和图片
- 不保留 OpenAI 兼容接口风格，使用前端专用任务接口
- 生产模式由 FastAPI 托管前端静态文件
- 不保留用户已明确否掉的能力：
  - `/api/images/{id}/thumbnail`
  - `raw_response_payload`
  - `raw_image_urls`

## 交付物

- `backend/` 可启动、可测试、可完成任务创建/执行/查询/删除/重试/图片访问
- `frontend/` 可构建、可测试、可通过后端完成生成/编辑/轮询/历史/详情/重试/删除/复用
- 前后端联调约束与设计与 [docs/PLAN.md](/home/veritas/works/image2-gen/docs/PLAN.md) 对齐

## 阶段 1：后端骨架

### 目标

建立可运行的 FastAPI 项目、配置系统、数据库和文件存储。

### 子步骤

1. 初始化 `uv` 虚拟环境与依赖
2. 建立 `pyproject.toml` / `requirements.txt`
3. 实现 `config.toml` 解析
4. 实现数据库初始化与 ORM 模型
5. 实现本地图片存储工具
6. 补基础测试

### 完成标准

- `uv run pytest` 中基础配置、数据库、文件存储测试通过
- FastAPI 能启动并加载配置

## 阶段 2：后端核心 API

### 目标

实现任务创建、执行、查询，以及图片访问。

### 子步骤

1. 实现 `POST /api/tasks`
2. 实现后台执行器和上游调用
3. 实现 `GET /api/tasks`
4. 实现 `GET /api/tasks/{id}`
5. 实现 `GET /api/images/{id}` 和 `/download`
6. 补集成测试覆盖生成和编辑流程

### 完成标准

- 可创建 generate/edit 任务
- 可轮询到 `succeeded/failed`
- 输出图片能访问和下载

## 阶段 3：后端完善

### 目标

补齐重试、删除、应用配置和生产托管。

### 子步骤

1. 实现 `POST /api/tasks/{id}/retry`
2. 实现 `DELETE /api/tasks/{id}`
3. 实现 `GET /api/app/config`
4. 接入生产静态托管
5. 补异常处理和错误信息
6. 回归测试

### 完成标准

- 删除、重试、配置接口均可用
- 生产模式可直接托管前端 `dist`

## 阶段 4：前端基础改造

### 目标

复制参考前端并切入后端代理模式。

### 子步骤

1. 复制 `refs/gpt_image_playground` 到 `frontend/`
2. 新增 `src/lib/backendApi.ts`
3. 改 `types.ts` 对齐后端任务模型
4. 收口设置面板，只保留 access token 和必要本地开关
5. 接入 `/api/app/config`
6. 保证前端可构建

### 完成标准

- `bun run build` 通过
- UI 中不再暴露 `apiKey/apiUrl/provider`

## 阶段 5：前端任务流对接

### 目标

把任务、历史、详情、图片展示全部切到后端。

### 子步骤

1. 重写 `store.ts` 的任务来源
2. 去掉本地任务持久化和旧恢复逻辑
3. 提交流程改为 `POST /api/tasks` + 轮询
4. 历史列表改为 `GET /api/tasks`
5. 详情页改为后端任务详情
6. 图片展示改为 `/api/images/{id}`
7. 改造重试、删除、编辑输出
8. 为 backend-first 流程补测试

### 完成标准

- 前端任务列表以后端为真相源
- 刷新后仍能恢复任务和图片展示

## 阶段 6：打磨与收尾

### 目标

去掉已否定设计，补联调验证，完成最终收口。

### 子步骤

1. 清理不再需要的字段和接口
2. 确认遮罩编辑流可用
3. 确认 `responses` 模式可用
4. 确认 `actual_params` / `revised_prompt` 展示
5. 确认测试矩阵覆盖前后端关键链路
6. 做完成度审计并记录证据

### 完成标准

- 前后端测试全部通过
- 用户已否掉的字段/接口不再残留在主链路
- 关键功能与 [docs/PLAN.md](/home/veritas/works/image2-gen/docs/PLAN.md) 一致

## 当前执行顺序

1. 补齐缺失计划文档
2. 完成后端与前端主链路
3. 清理残留旧字段与旧直连逻辑
4. 执行前后端测试
5. 做完成度审计
