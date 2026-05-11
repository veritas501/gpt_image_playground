import { describe, expect, it } from 'vitest'
import {
  DEFAULT_IMAGES_MODEL,
  DEFAULT_OPENAI_PROFILE_ID,
  DEFAULT_SETTINGS,
  getActiveApiProfile,
  mergeImportedSettings,
  normalizeSettings,
} from './apiProfiles'

describe('apiProfiles', () => {
  it('normalizes settings to a single active OpenAI profile', () => {
    const settings = normalizeSettings({
      accessToken: 'token',
      baseUrl: 'https://api.example.com/v1/',
      apiKey: 'upstream-key',
      model: 'custom-model',
      timeout: 300,
      apiMode: 'responses',
      codexCli: true,
      apiProxy: false,
    })

    expect(settings.activeProfileId).toBe(DEFAULT_OPENAI_PROFILE_ID)
    expect(settings.profiles).toHaveLength(1)
    expect(settings.profiles[0]).toMatchObject({
      provider: 'openai',
      baseUrl: 'https://api.example.com/v1',
      apiKey: 'upstream-key',
      model: 'custom-model',
      timeout: 300,
      apiMode: 'responses',
      codexCli: true,
      apiProxy: false,
    })
  })

  it('maps imported profile payload to the single active profile view', () => {
    const settings = normalizeSettings({
      profiles: [{
        id: 'imported-openai',
        name: 'Imported',
        provider: 'openai',
        baseUrl: 'https://imported.example.com/v1',
        apiKey: 'imported-key',
        model: 'imported-model',
        timeout: 120,
        apiMode: 'images',
        codexCli: false,
        apiProxy: true,
      }],
      activeProfileId: 'imported-openai',
    })

    expect(settings.activeProfileId).toBe('imported-openai')
    expect(settings.profiles[0]).toMatchObject({
      id: 'imported-openai',
      name: 'Imported',
      provider: 'openai',
      baseUrl: 'https://imported.example.com/v1',
      apiKey: 'imported-key',
      model: 'imported-model',
    })
  })

  it('defaults to clearing input after submit', () => {
    const settings = normalizeSettings({})

    expect(settings.clearInputAfterSubmit).toBe(true)
  })

  it('defaults to codex cli mode', () => {
    const settings = normalizeSettings({})

    expect(settings.codexCli).toBe(true)
    expect(DEFAULT_SETTINGS.codexCli).toBe(true)
  })

  it('keeps frontend-local settings when imported config omits them', () => {
    const merged = mergeImportedSettings(
      {
        ...DEFAULT_SETTINGS,
        accessToken: 'current-token',
        clearInputAfterSubmit: true,
        persistInputOnRestart: false,
        alwaysShowRetryButton: true,
      },
      {
        baseUrl: 'https://imported.example.com/v1',
        apiKey: 'imported-key',
        model: 'imported-model',
      },
    )

    expect(merged.accessToken).toBe('current-token')
    expect(merged.clearInputAfterSubmit).toBe(true)
    expect(merged.persistInputOnRestart).toBe(false)
    expect(merged.alwaysShowRetryButton).toBe(true)
    expect(merged.baseUrl).toBe('https://imported.example.com/v1')
    expect(merged.model).toBe('imported-model')
  })

  it('allows imported local frontend settings to override current ones', () => {
    const merged = mergeImportedSettings(DEFAULT_SETTINGS, {
      clearInputAfterSubmit: true,
      persistInputOnRestart: false,
      alwaysShowRetryButton: true,
      accessToken: 'imported-token',
    })

    expect(merged).toMatchObject({
      clearInputAfterSubmit: true,
      persistInputOnRestart: false,
      alwaysShowRetryButton: true,
      accessToken: 'imported-token',
    })
  })

  it('returns the normalized active profile', () => {
    const profile = getActiveApiProfile(DEFAULT_SETTINGS)

    expect(profile).toMatchObject({
      id: DEFAULT_OPENAI_PROFILE_ID,
      provider: 'openai',
      model: DEFAULT_IMAGES_MODEL,
    })
  })
})
