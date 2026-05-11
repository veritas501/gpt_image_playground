import { describe, expect, it } from 'vitest'
import { DEFAULT_SETTINGS } from './apiProfiles'
import { buildSettingsFromUrlParams, clearUrlSettingParams, hasUrlSettingParams } from './urlSettings'

describe('URL settings params', () => {
  it('ignores removed legacy URL config params', () => {
    const next = buildSettingsFromUrlParams(
      DEFAULT_SETTINGS,
      new URLSearchParams('apiUrl=https://api.example.com/v1&apiKey=test-key&model=test-model'),
    )

    expect(next).toEqual({})
  })

  it('clears only the supported settings param', () => {
    const params = new URLSearchParams('settings=%7B%7D&apiUrl=https://api.example.com/v1&foo=bar')

    expect(hasUrlSettingParams(params)).toBe(true)
    clearUrlSettingParams(params)

    expect(params.toString()).toBe('apiUrl=https%3A%2F%2Fapi.example.com%2Fv1&foo=bar')
  })

  it('imports only local frontend settings from URL params', () => {
    const params = new URLSearchParams()
    params.set('settings', JSON.stringify({
      clearInputAfterSubmit: true,
      persistInputOnRestart: false,
      alwaysShowRetryButton: true,
      profiles: [{
        id: 'should-be-ignored',
      }],
    }))

    const next = buildSettingsFromUrlParams(DEFAULT_SETTINGS, params)

    expect(next).toEqual({
      clearInputAfterSubmit: true,
      persistInputOnRestart: false,
      alwaysShowRetryButton: true,
    })
  })
})
