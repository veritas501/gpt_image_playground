import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DEFAULT_PARAMS } from './types'
import { DEFAULT_SETTINGS } from './lib/apiProfiles'
import type { TaskRecord } from './types'
import { editOutputs, getPersistedState, reuseConfig, submitTask, useStore } from './store'

const imageA = { id: 'image-a', dataUrl: 'data:image/png;base64,a' }

function task(overrides: Partial<TaskRecord> = {}): TaskRecord {
  return {
    id: 'task-a',
    prompt: 'prompt',
    params: { ...DEFAULT_PARAMS },
    inputImageIds: [],
    maskTargetImageId: null,
    maskImageId: null,
    outputImages: [],
    status: 'done',
    error: null,
    createdAt: 1,
    finishedAt: 2,
    elapsed: 1,
    ...overrides,
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('mask draft lifecycle in store actions', () => {
  beforeEach(() => {
    useStore.setState({
      settings: { ...DEFAULT_SETTINGS, apiKey: 'test-key' },
      prompt: 'prompt',
      inputImages: [],
      maskDraft: null,
      maskEditorImageId: null,
      params: { ...DEFAULT_PARAMS },
      tasks: [],
      detailTaskId: null,
      lightboxImageId: null,
      lightboxImageList: [],
      showSettings: false,
      toast: null,
      confirmDialog: null,
      showToast: vi.fn(),
      setConfirmDialog: vi.fn(),
    })
  })

  it('preserves an existing mask when quick edit-output adds outputs as references', async () => {
    const maskDraft = {
      targetImageId: imageA.id,
      maskDataUrl: 'data:image/png;base64,mask',
      updatedAt: 1,
    }
    useStore.setState({
      inputImages: [imageA],
      maskDraft,
    })

    await editOutputs(task({ outputImages: [imageA.id] }))

    expect(useStore.getState().maskDraft).toEqual(maskDraft)
  })

  it('clears an invalid mask draft when submit cannot find the mask target image', async () => {
    useStore.setState({
      inputImages: [imageA],
      maskDraft: {
        targetImageId: 'missing-image',
        maskDataUrl: 'data:image/png;base64,mask',
        updatedAt: 1,
      },
    })

    await submitTask()

    expect(useStore.getState().maskDraft).toBeNull()
  })
})

describe('backend-first task flow', () => {
  beforeEach(() => {
    useStore.setState({
      settings: { ...DEFAULT_SETTINGS, accessToken: 'token' },
      prompt: 'prompt',
      inputImages: [],
      maskDraft: null,
      maskEditorImageId: null,
      params: { ...DEFAULT_PARAMS },
      tasks: [],
      detailTaskId: null,
      lightboxImageId: null,
      lightboxImageList: [],
      showSettings: false,
      toast: null,
      confirmDialog: null,
      showToast: vi.fn(),
      setConfirmDialog: vi.fn(),
    })
  })

  it('hydrates tasks from backend detail after submit instead of creating a local pseudo task', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === '/api/tasks' && init?.method === 'POST') {
        return new Response(JSON.stringify({
          request_id: 'backend-task-1',
          status: 'queued',
          created_at: '2026-05-11T09:00:00Z',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      if (url === '/api/tasks/backend-task-1' && init?.method === 'POST') {
        return new Response(JSON.stringify({
          request_id: 'backend-task-1',
          prompt: 'prompt',
          mode: 'generate',
          params: { ...DEFAULT_PARAMS },
          status: 'succeeded',
          error: null,
          api_mode: 'images',
          api_model: 'gpt-image-1',
          elapsed_ms: 5000,
          actual_params: { n: 1 },
          revised_prompt: null,
          input_image_ids: [],
          mask_image_id: null,
          output_image_ids: ['image-1'],
          created_at: '2026-05-11T09:00:00Z',
          started_at: '2026-05-11T09:00:01Z',
          finished_at: '2026-05-11T09:00:05Z',
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      throw new Error(`unexpected fetch: ${url}`)
    })

    await submitTask()

    expect(fetchMock).toHaveBeenCalledWith('/api/tasks', expect.objectContaining({ method: 'POST' }))
    expect(useStore.getState().tasks).toHaveLength(1)
    expect(useStore.getState().tasks[0]).toMatchObject({
      id: 'backend-task-1',
      status: 'done',
      outputImages: ['image-1'],
      apiModel: 'gpt-image-1',
    })
    expect(useStore.getState().taskIds).toEqual(['backend-task-1'])
    expect(useStore.getState().showToast).toHaveBeenCalledWith('生成完成，共 1 张图片', 'success')
  })
})

describe('input persistence setting', () => {
  beforeEach(() => {
    useStore.setState({
      settings: { ...DEFAULT_SETTINGS },
      taskIds: [],
      prompt: 'prompt',
      inputImages: [imageA],
      dismissedCodexCliPrompts: [],
    })
  })

  it('persists input when restart input restore is enabled', () => {
    const persisted = getPersistedState(useStore.getState())

    expect(persisted.prompt).toBe('prompt')
    expect(persisted.inputImages).toEqual([{ id: imageA.id, dataUrl: '' }])
    expect(persisted.taskIds).toEqual([])
  })

  it('omits input when restart input restore is disabled', () => {
    useStore.setState({ settings: { ...DEFAULT_SETTINGS, persistInputOnRestart: false } })

    const persisted = getPersistedState(useStore.getState())

    expect(persisted).not.toHaveProperty('prompt')
    expect(persisted).not.toHaveProperty('inputImages')
  })

  it('writes empty input when persisted input is cleared', () => {
    useStore.setState({ prompt: '', inputImages: [] })

    const persisted = getPersistedState(useStore.getState())

    expect(persisted.prompt).toBe('')
    expect(persisted.inputImages).toEqual([])
  })
})

describe('reuse task config', () => {
  beforeEach(() => {
    useStore.setState({
      settings: { ...DEFAULT_SETTINGS, accessToken: 'token' },
      prompt: '',
      inputImages: [],
      maskDraft: null,
      params: { ...DEFAULT_PARAMS },
      tasks: [],
      showSettings: false,
      toast: null,
      showToast: vi.fn(),
    })
  })

  it('reuses task params directly into the input area', async () => {
    await reuseConfig(task({
      params: { ...DEFAULT_PARAMS, n: 8, size: 'auto', quality: 'auto' },
    }))

    const state = useStore.getState()
    expect(state.params).toMatchObject({ n: 8, size: 'auto', quality: 'auto' })
    expect(state.showToast).toHaveBeenCalledWith('已复用配置到输入框', 'success')
  })
})
