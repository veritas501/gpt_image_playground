import { describe, expect, it } from 'vitest'
import { DEFAULT_PARAMS } from '../types'
import { DEFAULT_SETTINGS, normalizeSettings } from './apiProfiles'
import { getOutputImageLimitForSettings, normalizeParamsForSettings } from './paramCompatibility'

describe('parameter compatibility', () => {
  it('limits output count to backend cap', () => {
    const settings = normalizeSettings(DEFAULT_SETTINGS)

    expect(getOutputImageLimitForSettings(settings)).toBe(10)
    expect(normalizeParamsForSettings({ ...DEFAULT_PARAMS, n: 12 }, settings).n).toBe(10)
  })

  it('keeps auto size unchanged', () => {
    const settings = normalizeSettings(DEFAULT_SETTINGS)

    expect(normalizeParamsForSettings({ ...DEFAULT_PARAMS, size: 'auto' }, settings).size).toBe('auto')
  })

  it('clears output compression for png', () => {
    const settings = normalizeSettings(DEFAULT_SETTINGS)

    expect(
      normalizeParamsForSettings({
        ...DEFAULT_PARAMS,
        output_format: 'png',
        output_compression: 75,
      }, settings).output_compression,
    ).toBeNull()
  })
})
