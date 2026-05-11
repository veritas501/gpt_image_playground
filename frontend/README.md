# frontend

内部专用图片生成客户端。

当前前端已经不是原始参考项目那种“浏览器直连 OpenAI/兼容接口”的架构，而是专门服务于本仓库后端：

- 只请求本仓库 `backend/` 暴露的 `/api/*`
- 只在本地保存 `X-Access-Token` 与 `request_id[]`
- 不暴露 `apiKey / apiUrl / provider` 配置

## 运行

```bash
cd "./frontend"
bun install
bun run dev --host 0.0.0.0 --port 5173
```

## 构建

```bash
cd "./frontend"
bun run build
```

## 测试

```bash
cd "./frontend"
bun run test
```

## 当前职责

- 提交文生图与编辑任务
- 本地保存任务 ID
- 轮询任务详情
- 展示输出图
- 缓存缩略图
- 支持结果复用与遮罩编辑

## 历史资料

`docs/` 目录下保留了一些从参考前端项目继承来的资料和截图，主要用于视觉/交互参考，不作为当前项目的权威运行说明。

当前项目的权威文档在仓库根目录 `docs/`。
