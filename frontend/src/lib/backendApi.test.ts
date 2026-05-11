import { afterEach, describe, expect, it, vi } from 'vitest'

import { getBackendTask } from './backendApi'
import { DEFAULT_SETTINGS } from './apiProfiles'

describe('backendApi', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('requests task detail with cache disabled', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({
        request_id: 'task-1',
        prompt: 'prompt',
        mode: 'generate',
        params: {},
        status: 'running',
        error: null,
        api_mode: 'images',
        api_model: 'gpt-image-2',
        elapsed_ms: null,
        actual_params: null,
        revised_prompt: null,
        input_image_ids: [],
        mask_image_id: null,
        output_image_ids: [],
        created_at: '2026-05-11T09:00:00Z',
        started_at: '2026-05-11T09:00:01Z',
        finished_at: null,
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      },
    ))

    await getBackendTask({ ...DEFAULT_SETTINGS, accessToken: 'token' }, 'task-1')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/tasks/task-1',
      expect.objectContaining({
        method: 'POST',
        cache: 'no-store',
        headers: expect.objectContaining({
          'X-Access-Token': 'token',
        }),
      }),
    )
  })
})
