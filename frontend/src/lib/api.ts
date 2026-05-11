import {
  buildBackendImageUrl,
  createBackendTask,
  getBackendTask,
} from './backendApi'
import type { CallApiOptions, CallApiResult } from './imageApiShared'
import {
  fetchImageUrlAsDataUrl,
  getDataUrlDecodedByteSize,
  MIME_MAP,
} from './imageApiShared'

export type { CallApiOptions, CallApiResult } from './imageApiShared'
export { normalizeBaseUrl } from './devProxy'

const TASK_POLL_INTERVAL_MS = 1500

export async function callImageApi(opts: CallApiOptions): Promise<CallApiResult> {
  const inputFiles = await Promise.all(
    opts.inputImageDataUrls.map((dataUrl, index) =>
      dataUrlToFile(dataUrl, `input-${index}.${extensionForMime(dataUrl)}`),
    ),
  )
  const maskFile = opts.maskDataUrl
    ? await dataUrlToFile(opts.maskDataUrl, `mask.${extensionForMime(opts.maskDataUrl)}`)
    : null

  const created = await createBackendTask(opts.settings, {
    prompt: opts.prompt,
    mode: inputFiles.length > 0 ? 'edit' : 'generate',
    params: opts.params,
    inputImages: inputFiles,
    mask: maskFile,
    maskTargetIndex: maskFile ? 0 : null,
  })
  opts.onCustomTaskEnqueued?.({ taskId: created.request_id })

  const detail = await waitForTask(opts, created.request_id)
  const mime = MIME_MAP[opts.params.output_format] || 'image/png'
  const images = await Promise.all(
    detail.output_image_ids.map((imageId) => fetchImageUrlAsDataUrl(buildBackendImageUrl(imageId), mime)),
  )
  const revisedPrompts = detail.revised_prompt
    ? detail.output_image_ids.map(() => detail.revised_prompt ?? undefined)
    : undefined

  return {
    images,
    actualParams: detail.actual_params ?? undefined,
    actualParamsList: detail.actual_params ? detail.output_image_ids.map(() => detail.actual_params ?? undefined) : undefined,
    revisedPrompts,
  }
}

async function waitForTask(opts: CallApiOptions, requestId: string) {
  const timeoutMs = Math.max(10_000, opts.settings.timeout * 1000)
  const deadline = Date.now() + timeoutMs

  while (Date.now() <= deadline) {
    const detail = await getBackendTask(opts.settings, requestId)
    if (detail.status === 'succeeded') return detail
    if (detail.status === 'failed') {
      throw new Error(detail.error || '后端任务执行失败')
    }
    await sleep(TASK_POLL_INTERVAL_MS)
  }

  throw new Error(`请求超时：超过 ${opts.settings.timeout} 秒仍未完成，请稍后重试。`)
}

async function dataUrlToFile(dataUrl: string, filename: string): Promise<File> {
  const response = await fetch(dataUrl)
  const blob = await response.blob()
  return new File([blob], filename, { type: blob.type || 'application/octet-stream' })
}

function extensionForMime(dataUrl: string): string {
  const mime = dataUrl.slice(5, dataUrl.indexOf(';'))
  if (mime === 'image/jpeg') return 'jpg'
  if (mime === 'image/webp') return 'webp'
  if (mime === 'image/png') return 'png'
  return 'bin'
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}
