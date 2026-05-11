# 架构说明

## 总览

当前项目采用前后端一体交付、责任分离的结构：

```text
Browser SPA -> FastAPI -> Internal Upstream API
```

其中：

- 前端只负责交互与展示
- 后端负责所有敏感配置、上游调用与数据持久化
- 图片与任务元数据都在服务端保存

## 职责划分

### frontend/

负责：

- 提示词输入与参数编辑
- 参考图、遮罩图上传
- 本地保存 `request_id[]`
- 轮询任务详情
- 图片展示、下载、复用
- 内部专用设置项

不负责：

- 保存上游 API Key
- 保存上游 Base URL
- Provider 选择
- 直接请求内网上游

### backend/

负责：

- 校验 `X-Access-Token`
- 接收前端任务请求
- 落盘输入图、遮罩图、输出图
- 将任务写入 SQLite
- 后台线程执行上游请求
- 暴露任务详情与图片读取接口
- 生产环境托管前端 `dist/`

### data/

负责运行时持久化：

- `backend/app.db`：SQLite 数据库
- `data/images/`：输入图、遮罩图、输出图等文件

## 数据流

### 创建任务

1. 前端 `POST /api/tasks`
2. 后端保存任务元数据与上传文件
3. 后端立即返回 `request_id`
4. 后台线程调用上游接口
5. 后端保存输出图并更新任务状态
6. 前端按 `request_id` 轮询详情并展示结果

### 页面刷新恢复

1. 前端从本地存储取出 `request_id[]`
2. 逐个请求 `POST /api/tasks/{request_id}`
3. 成功则恢复历史卡片
4. 若任务完成，再请求 `/api/images/{image_id}` 展示图片

## 目录约定

```text
frontend/
  src/
  public/
  docs/
backend/
  app/
    routers/
    repositories/
    services/
    utils/
  tests/
data/
  images/
docs/
```

## 权威原则

- 设计决策以 `docs/PLAN.md` 为准
- 实际运行行为以 `backend/app/` 与 `frontend/src/` 为准
- 旧参考前端文档不能覆盖当前项目架构
