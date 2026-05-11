# 开发指南

## 环境要求

- `bun`
- `uv`
- Python 3.12+
- Node.js 仅作为部分前端生态依赖兼容环境

## 初始化

### 前端

```bash
cd "./frontend"
bun install
```

### 后端

```bash
cd "./backend"
uv venv
uv sync
cp "./config.example.toml" "./config.toml"
```

然后按实际环境修改 `config.toml`：

- `security.access_token`
- `upstream.base_url`
- `upstream.api_key`
- `upstream.default_model`

## 本地开发启动

### 启动后端

```bash
cd "./backend"
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

### 启动前端

```bash
cd "./frontend"
bun run dev --host 0.0.0.0 --port 5173
```

## 测试

### 前端测试

```bash
cd "./frontend"
bun run test
```

### 后端测试

`uv sync` 默认不带测试依赖；跑测试前需要同步 test extra。

```bash
cd "./backend"
uv sync --extra test
uv run pytest
```

## 联调检查清单

1. `GET /api/health` 返回 `{"status":"ok"}`
2. `GET /api/app/config` 能返回前端运行配置
3. 前端设置中填入正确 `X-Access-Token`
4. 创建任务后前端能拿到 `request_id`
5. 任务完成后 `/api/tasks/{id}` 返回 `output_image_ids`
6. `/api/images/{image_id}` 能直接返回图片流

## 常见注意事项

- 前端任务详情轮询已经改为 `POST /api/tasks/{request_id}`，用于规避浏览器或代理层对 GET 的缓存干扰
- 前端本地只保存 `request_id[]`，后端不提供全量任务列表接口
- `frontend/docs/` 里的旧文档描述的是参考前端项目，不代表当前运行方式
