import { beforeEach, describe, expect, it, vi } from 'vitest'

const imageStore = new Map<string, { id: string; dataUrl: string; createdAt?: number; source?: 'upload' | 'generated' | 'mask'; width?: number; height?: number }>()
const thumbnailStore = new Map<string, { id: string; thumbnailDataUrl: string; width?: number; height?: number; thumbnailVersion?: number }>()

vi.mock('./lib/db', () => ({
  CURRENT_THUMBNAIL_VERSION: 2,
  getImage: vi.fn(async (id: string) => imageStore.get(id)),
  getStoredFreshImageThumbnail: vi.fn(async (id: string) => thumbnailStore.get(id)),
  getImageThumbnail: vi.fn(async (id: string) => {
    if (!imageStore.has(id)) return undefined
    const thumbnail = {
      id,
      thumbnailDataUrl: 'data:image/webp;base64,dGh1bWI=',
      width: 1024,
      height: 1024,
      thumbnailVersion: 2,
    }
    thumbnailStore.set(id, thumbnail)
    return thumbnail
  }),
  getStoredImageThumbnail: vi.fn(async (id: string) => thumbnailStore.get(id)),
  putImage: vi.fn(async (image: { id: string; dataUrl: string; createdAt?: number; source?: 'upload' | 'generated' | 'mask'; width?: number; height?: number }) => {
    imageStore.set(image.id, image)
    return image.id
  }),
  putImageThumbnail: vi.fn(async (thumbnail: { id: string; thumbnailDataUrl: string; width?: number; height?: number; thumbnailVersion?: number }) => {
    thumbnailStore.set(thumbnail.id, thumbnail)
    return thumbnail.id
  }),
  deleteImage: vi.fn(async () => undefined),
  clearImages: vi.fn(async () => {
    imageStore.clear()
    thumbnailStore.clear()
    return undefined
  }),
  getAllImageIds: vi.fn(async () => []),
  getAllImages: vi.fn(async () => []),
  storeImage: vi.fn(),
  putTask: vi.fn(),
  getAllTasks: vi.fn(async () => []),
  deleteTask: vi.fn(async () => undefined),
  clearTasks: vi.fn(async () => undefined),
}))

vi.mock('./lib/imageApiShared', async () => {
  const actual = await vi.importActual<typeof import('./lib/imageApiShared')>('./lib/imageApiShared')
  return {
    ...actual,
    fetchImageUrlAsDataUrl: vi.fn(async () => 'data:image/png;base64,cmVtb3Rl'),
  }
})

import { DEFAULT_SETTINGS } from './lib/apiProfiles'
import { ensureImageThumbnailCached, useStore } from './store'

describe('ensureImageThumbnailCached', () => {
  beforeEach(() => {
    imageStore.clear()
    thumbnailStore.clear()
    vi.restoreAllMocks()
    useStore.setState({
      settings: { ...DEFAULT_SETTINGS, accessToken: 'token' },
      tasks: [],
      taskIds: [],
      inputImages: [],
      toast: null,
    })
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) !== '/api/images/image-1') {
        throw new Error(`unexpected fetch: ${String(input)}`)
      }
      return new Response('remote-image', {
        status: 200,
        headers: { 'Content-Type': 'image/png' },
      })
    }))
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:mock'),
      revokeObjectURL: vi.fn(),
    })
  })

  it('returns a generated thumbnail immediately after fetching a remote backend image', async () => {
    const thumbnail = await ensureImageThumbnailCached('image-1')

    expect(thumbnail).toEqual({
      dataUrl: 'data:image/webp;base64,dGh1bWI=',
      width: 1024,
      height: 1024,
      thumbnailVersion: 2,
    })
  })
})
