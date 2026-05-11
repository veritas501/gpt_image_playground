import { afterEach, describe, expect, it, vi } from 'vitest'
import { DEFAULT_PARAMS, type BackendTaskDetail } from '../types'
import { DEFAULT_SETTINGS } from './apiProfiles'
import { callImageApi } from './api'

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('callImageApi', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a backend task, polls detail, and fetches output images', async () => {
    const detail: BackendTaskDetail = {
      request_id: 'task-1',
      prompt: 'prompt',
      mode: 'generate',
      params: { ...DEFAULT_PARAMS },
      status: 'succeeded',
      error: null,
      api_mode: 'images',
      api_model: 'gpt-image-1',
      elapsed_ms: 1234,
      actual_params: { size: '1024x1024', n: 1 },
      revised_prompt: 'revised prompt',
      input_image_ids: [],
      mask_image_id: null,
      output_image_ids: ['image-1'],
      created_at: '2026-05-11T09:00:00Z',
      started_at: '2026-05-11T09:00:01Z',
      finished_at: '2026-05-11T09:00:02Z',
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/tasks' && init?.method === 'POST') {
        return jsonResponse({
          request_id: 'task-1',
          status: 'queued',
          created_at: '2026-05-11T09:00:00Z',
        })
      }
      if (url === '/api/tasks/task-1') {
        return jsonResponse(detail)
      }
      if (url === '/api/images/image-1') {
        return new Response('image', {
          status: 200,
          headers: { 'Content-Type': 'image/png' },
        })
      }
      throw new Error(`unexpected fetch: ${url}`)
    })

    const onCustomTaskEnqueued = vi.fn()
    const result = await callImageApi({
      settings: { ...DEFAULT_SETTINGS, accessToken: 'token' },
      prompt: 'prompt',
      params: { ...DEFAULT_PARAMS },
      inputImageDataUrls: [],
      onCustomTaskEnqueued,
    })

    expect(onCustomTaskEnqueued).toHaveBeenCalledWith({ taskId: 'task-1' })
    expect(result).toEqual({
      images: ['data:image/png;base64,aW1hZ2U='],
      actualParams: { size: '1024x1024', n: 1 },
      actualParamsList: [{ size: '1024x1024', n: 1 }],
      revisedPrompts: ['revised prompt'],
    })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('throws the backend task error when polling reaches failed state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/tasks' && init?.method === 'POST') {
        return jsonResponse({
          request_id: 'task-2',
          status: 'queued',
          created_at: '2026-05-11T09:00:00Z',
        })
      }
      if (url === '/api/tasks/task-2') {
        return jsonResponse({
          request_id: 'task-2',
          prompt: 'prompt',
          mode: 'generate',
          params: { ...DEFAULT_PARAMS },
          status: 'failed',
          error: 'upstream failed',
          api_mode: 'images',
          api_model: 'gpt-image-1',
          elapsed_ms: 1234,
          actual_params: null,
          revised_prompt: null,
          input_image_ids: [],
          mask_image_id: null,
          output_image_ids: [],
          created_at: '2026-05-11T09:00:00Z',
          started_at: '2026-05-11T09:00:01Z',
          finished_at: '2026-05-11T09:00:02Z',
        })
      }
      throw new Error(`unexpected fetch: ${url}`)
    })

    await expect(callImageApi({
      settings: { ...DEFAULT_SETTINGS, accessToken: 'token' },
      prompt: 'prompt',
      params: { ...DEFAULT_PARAMS },
      inputImageDataUrls: [],
    })).rejects.toThrow('upstream failed')
  })
})
