# 后端 API

所有 `/api/*` 接口默认要求：

```http
X-Access-Token: <token>
```

公开接口只有：

- `GET /api/health`

## `GET /api/health`

健康检查。

返回：

```json
{"status":"ok"}
```

## `GET /api/app/config`

返回前端运行时可见的非敏感配置。

返回字段：

- `app_name`
- `default_model`
- `api_mode`
- `supported_sizes`
- `default_params`

## `POST /api/tasks`

创建生成或编辑任务。

请求类型：`multipart/form-data`

字段：

- `prompt`: 提示词
- `mode`: `generate` 或 `edit`
- `params`: JSON 字符串
- `input_images`: 参考图数组
- `mask`: 遮罩图
- `mask_target_index`: 遮罩目标图索引
- `n`
- `size`
- `quality`
- `output_format`
- `output_compression`
- `moderation`

返回：

```json
{
  "request_id": "<id>",
  "status": "queued",
  "created_at": "2026-05-11T10:00:00Z"
}
```

## `GET /api/tasks/{request_id}`

读取任务详情。主要用于排查和 `curl` 调试。

## `POST /api/tasks/{request_id}`

读取任务详情。

这是前端默认使用的接口，语义上等同于上面的 GET，但可以规避部分浏览器或代理的缓存问题。

任务详情字段包含：

- `request_id`
- `prompt`
- `mode`
- `params`
- `status`
- `error`
- `api_mode`
- `api_model`
- `elapsed_ms`
- `actual_params`
- `revised_prompt`
- `input_image_ids`
- `mask_image_id`
- `output_image_ids`
- `created_at`
- `started_at`
- `finished_at`

## `POST /api/tasks/{request_id}/retry`

基于原任务重新创建一个新任务，返回新的 `request_id`。

## `DELETE /api/tasks/{request_id}`

删除任务。

查询参数：

- `keep_images=true|false`

默认 `false` 时会一并删除关联图片。

## `GET /api/images/{image_id}`

直接返回图片二进制流。

## `GET /api/images/{image_id}/download`

返回图片下载流，并带 `Content-Disposition: attachment`。

## 已明确不提供的接口

- 不提供全量 `GET /api/tasks`
- 不提供 `/api/images/{image_id}/thumbnail`

原因：

- 任务列表改为前端仅保存自己的 `request_id[]`
- 缩略图缓存由前端本地逻辑处理
