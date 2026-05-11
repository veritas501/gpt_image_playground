import type {
  AppSettings,
  BackendAppConfig,
  BackendTaskCreateResponse,
  BackendTaskDetail,
  TaskParams,
} from '../types'
import { getApiErrorMessage } from './imageApiShared'

export interface CreateBackendTaskInput {
  prompt: string
  mode: 'generate' | 'edit'
  params: Partial<TaskParams>
  inputImages?: File[]
  mask?: File | null
  maskTargetIndex?: number | null
}

function getAccessToken(settings: Pick<AppSettings, 'accessToken'>): string {
  return settings.accessToken.trim()
}

async function requestJson<T>(
  path: string,
  settings: Pick<AppSettings, 'accessToken'>,
  init?: RequestInit,
): Promise<T> {
  const token = getAccessToken(settings)
  const response = await fetch(path, {
    cache: 'no-store',
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { 'X-Access-Token': token } : {}),
    },
  })
  if (!response.ok) {
    throw new Error(await getApiErrorMessage(response))
  }
  return response.json() as Promise<T>
}

export async function getBackendAppConfig(settings: Pick<AppSettings, 'accessToken'>): Promise<BackendAppConfig> {
  return requestJson<BackendAppConfig>('/api/app/config', settings)
}

export async function createBackendTask(
  settings: Pick<AppSettings, 'accessToken'>,
  input: CreateBackendTaskInput,
): Promise<BackendTaskCreateResponse> {
  const formData = new FormData()
  formData.set('prompt', input.prompt)
  formData.set('mode', input.mode)
  formData.set('params', JSON.stringify(input.params))
  if (input.maskTargetIndex != null) formData.set('mask_target_index', String(input.maskTargetIndex))
  for (const image of input.inputImages ?? []) formData.append('input_images', image)
  if (input.mask) formData.set('mask', input.mask)
  return requestJson<BackendTaskCreateResponse>('/api/tasks', settings, {
    method: 'POST',
    body: formData,
  })
}

export async function getBackendTask(
  settings: Pick<AppSettings, 'accessToken'>,
  requestId: string,
): Promise<BackendTaskDetail> {
  return requestJson<BackendTaskDetail>(`/api/tasks/${requestId}`, settings, {
    method: 'POST',
  })
}

export async function retryBackendTask(
  settings: Pick<AppSettings, 'accessToken'>,
  requestId: string,
): Promise<BackendTaskCreateResponse> {
  return requestJson<BackendTaskCreateResponse>(`/api/tasks/${requestId}/retry`, settings, {
    method: 'POST',
  })
}

export async function deleteBackendTask(
  settings: Pick<AppSettings, 'accessToken'>,
  requestId: string,
  keepImages = false,
): Promise<void> {
  const query = keepImages ? '?keep_images=true' : ''
  await requestJson<{ deleted: boolean }>(`/api/tasks/${requestId}${query}`, settings, {
    method: 'DELETE',
  })
}

export function buildBackendImageUrl(imageId: string): string {
  return `/api/images/${imageId}`
}

export function buildBackendImageDownloadUrl(imageId: string): string {
  return `/api/images/${imageId}/download`
}
