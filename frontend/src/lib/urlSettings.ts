import type { AppSettings } from '../types'

const URL_SETTING_KEYS = ['settings']

type UrlSettingsPayload = Pick<
  AppSettings,
  'clearInputAfterSubmit' | 'persistInputOnRestart' | 'alwaysShowRetryButton'
>

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function pickUrlSettingsPayload(value: unknown): Partial<UrlSettingsPayload> | null {
  if (!isRecord(value)) return null

  const patch: Partial<UrlSettingsPayload> = {}
  if (typeof value.clearInputAfterSubmit === 'boolean') patch.clearInputAfterSubmit = value.clearInputAfterSubmit
  if (typeof value.persistInputOnRestart === 'boolean') patch.persistInputOnRestart = value.persistInputOnRestart
  if (typeof value.alwaysShowRetryButton === 'boolean') patch.alwaysShowRetryButton = value.alwaysShowRetryButton

  return Object.keys(patch).length ? patch : null
}

function getUrlSettingsPayload(searchParams: URLSearchParams): Partial<UrlSettingsPayload> | null {
  const raw = searchParams.get('settings')
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw)
    if (isRecord(parsed) && 'settings' in parsed) {
      return pickUrlSettingsPayload(parsed.settings)
    }
    return pickUrlSettingsPayload(parsed)
  } catch {
    return null
  }
}

export function hasUrlSettingParams(searchParams: URLSearchParams) {
  return URL_SETTING_KEYS.some((key) => searchParams.has(key))
}

export function clearUrlSettingParams(searchParams: URLSearchParams) {
  for (const key of URL_SETTING_KEYS) searchParams.delete(key)
}

export function buildSettingsFromUrlParams(_currentSettings: Partial<AppSettings> | unknown, searchParams: URLSearchParams): Partial<AppSettings> {
  return getUrlSettingsPayload(searchParams) ?? {}
}
