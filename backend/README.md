# backend

FastAPI 后端，负责把前端请求代理到内网上游图片接口，并持久化任务与图片。

## 责任

- `X-Access-Token` 鉴权
- 任务创建、查询、重试、删除
- 上游 `images/generations` / `images/edits` 调用
- SQLite 元数据存储
- 本地文件系统图片存储
- 生产环境托管前端静态文件

## 运行

```bash
cd "./backend"
uv venv
uv sync
cp "./config.example.toml" "./config.toml"
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

## 测试

```bash
cd "./backend"
uv sync --extra test
uv run pytest
```

## 关键文件

- `app/main.py`: 应用入口、鉴权中间件、静态托管
- `app/routers/tasks.py`: 任务接口
- `app/routers/images.py`: 图片接口
- `app/services/task_service.py`: 任务业务逻辑
- `app/services/upstream.py`: 上游 HTTP 调用
- `app/utils/file_storage.py`: 文件落盘与读取
- `config.example.toml`: 配置模板
