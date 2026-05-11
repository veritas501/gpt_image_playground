# 生产部署

## 部署形态

生产环境采用单机单进程的简单内网部署：

- 先构建前端静态文件
- 再由 FastAPI 同时提供 API 与静态资源
- 对外只暴露一个端口

## 构建前端

```bash
cd "./frontend"
bun install
bun run build
```

构建产物默认输出到 `frontend/dist/`。

## 准备后端

```bash
cd "./backend"
uv venv
uv sync
cp "./config.example.toml" "./config.toml"
```

按内网环境修改 `config.toml`。

## 启动服务

```bash
cd "./backend"
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

## 配置说明

### `security.access_token`

前端访问后端时必须携带的固定口令：

```http
X-Access-Token: <token>
```

### `upstream.timeout_seconds`

后端请求内网上游时的 HTTP 超时秒数。

它约束的是：

- 建连等待
- 上游处理等待
- 响应体读取等待

不是前端轮询超时，也不是整个任务生命周期上限。

### `app.static_dir`

生产静态文件目录。默认值是：

```toml
static_dir = "../frontend/dist"
```

## 反向代理

如果需要挂到现有网关或 Nginx 后面：

- 保持所有 `/api/*` 请求转发到 FastAPI
- 其余路径也转发给 FastAPI，用于返回 SPA 静态资源
- 不要额外缓存 `/api/app/*` 与 `/api/tasks/*`

## 持久化建议

至少持久化以下路径：

- `backend/app.db`
- `data/images/`
- `backend/config.toml`

否则重启后会丢失任务元数据、图片文件或运行配置。
