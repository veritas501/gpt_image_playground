import type { ApiMode, ApiProfile, AppSettings } from '../types'
import { readRuntimeEnv } from './runtimeEnv'

const DEFAULT_BASE_URL = readRuntimeEnv(import.meta.env.VITE_DEFAULT_API_URL) || 'https://api.openai.com/v1'
const DEFAULT_OPENAI_API_PROXY = readRuntimeEnv(import.meta.env.VITE_API_PROXY_AVAILABLE) === 'true'

export const DEFAULT_IMAGES_MODEL = 'gpt-image-2'
export const DEFAULT_RESPONSES_MODEL = 'gpt-5.5'
export const DEFAULT_OPENAI_PROFILE_ID = 'default-openai'
export const DEFAULT_API_TIMEOUT = 600

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function normalizeApiMode(value: unknown, fallback: ApiMode = 'images'): ApiMode {
  return value === 'responses' ? 'responses' : fallback
}

function normalizeTimeout(value: unknown, fallback = DEFAULT_API_TIMEOUT): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : fallback
}

function pickImportedProfile(record: Record<string, unknown>): Partial<ApiProfile> | null {
  if (!Array.isArray(record.profiles) || record.profiles.length === 0) return null
  const first = record.profiles.find(isRecord)
  if (!first) return null

  return {
    id: typeof first.id === 'string' && first.id.trim() ? first.id.trim() : DEFAULT_OPENAI_PROFILE_ID,
    name: typeof first.name === 'string' && first.name.trim() ? first.name.trim() : '默认',
    provider: 'openai',
    baseUrl: typeof first.baseUrl === 'string' && first.baseUrl.trim() ? first.baseUrl.trim().replace(/\/+$/, '') : undefined,
    apiKey: typeof first.apiKey === 'string' ? first.apiKey : undefined,
    model: typeof first.model === 'string' && first.model.trim() ? first.model.trim() : undefined,
    timeout: normalizeTimeout(first.timeout, undefined),
    apiMode: normalizeApiMode(first.apiMode, undefined),
    codexCli: typeof first.codexCli === 'boolean' ? first.codexCli : undefined,
    apiProxy: typeof first.apiProxy === 'boolean' ? first.apiProxy : undefined,
  }
}

export function createDefaultOpenAIProfile(overrides: Partial<ApiProfile> = {}): ApiProfile {
  return {
    id: DEFAULT_OPENAI_PROFILE_ID,
    name: '默认',
    provider: 'openai',
    baseUrl: DEFAULT_BASE_URL,
    apiKey: '',
    model: DEFAULT_IMAGES_MODEL,
    timeout: DEFAULT_API_TIMEOUT,
    apiMode: 'images',
    codexCli: true,
    apiProxy: DEFAULT_OPENAI_API_PROXY,
    responseFormatB64Json: false,
    ...overrides,
  }
}

export function normalizeSettings(input: Partial<AppSettings> | unknown): AppSettings {
  const record = isRecord(input) ? input : {}
  const importedProfile = pickImportedProfile(record)
  const baseProfile = createDefaultOpenAIProfile(importedProfile ?? {})

  const profile: ApiProfile = {
    ...baseProfile,
    id: typeof record.activeProfileId === 'string' && record.activeProfileId.trim()
      ? record.activeProfileId.trim()
      : baseProfile.id,
    name: typeof record.name === 'string' && record.name.trim()
      ? record.name.trim()
      : baseProfile.name,
    baseUrl: typeof record.baseUrl === 'string' && record.baseUrl.trim()
      ? record.baseUrl.trim().replace(/\/+$/, '')
      : baseProfile.baseUrl,
    apiKey: typeof record.apiKey === 'string'
      ? record.apiKey
      : baseProfile.apiKey,
    model: typeof record.model === 'string' && record.model.trim()
      ? record.model.trim()
      : baseProfile.model,
    timeout: normalizeTimeout(record.timeout, baseProfile.timeout),
    apiMode: normalizeApiMode(record.apiMode, baseProfile.apiMode),
    codexCli: typeof record.codexCli === 'boolean' ? record.codexCli : baseProfile.codexCli,
    apiProxy: typeof record.apiProxy === 'boolean' ? record.apiProxy : baseProfile.apiProxy,
  }

  return {
    accessToken: typeof record.accessToken === 'string' ? record.accessToken : '',
    baseUrl: profile.baseUrl,
    apiKey: profile.apiKey,
    model: profile.model,
    timeout: profile.timeout,
    apiMode: profile.apiMode,
    codexCli: profile.codexCli,
    apiProxy: profile.apiProxy,
    clearInputAfterSubmit: typeof record.clearInputAfterSubmit === 'boolean' ? record.clearInputAfterSubmit : true,
    persistInputOnRestart: typeof record.persistInputOnRestart === 'boolean' ? record.persistInputOnRestart : true,
    alwaysShowRetryButton: typeof record.alwaysShowRetryButton === 'boolean' ? record.alwaysShowRetryButton : false,
    profiles: [profile],
    activeProfileId: profile.id,
  }
}

export function getActiveApiProfile(settings: Partial<AppSettings> | unknown): ApiProfile {
  return normalizeSettings(settings).profiles[0]
}

export function mergeImportedSettings(currentSettings: Partial<AppSettings> | unknown, importedSettings: Partial<AppSettings> | unknown): AppSettings {
  const current = normalizeSettings(currentSettings)
  const imported = normalizeSettings(importedSettings)
  const importedRecord = isRecord(importedSettings) ? importedSettings : {}

  return normalizeSettings({
    ...current,
    accessToken: typeof importedRecord.accessToken === 'string' ? imported.accessToken : current.accessToken,
    baseUrl: imported.baseUrl,
    apiKey: imported.apiKey,
    model: imported.model,
    timeout: imported.timeout,
    apiMode: imported.apiMode,
    codexCli: imported.codexCli,
    apiProxy: imported.apiProxy,
    clearInputAfterSubmit:
      typeof importedRecord.clearInputAfterSubmit === 'boolean'
        ? imported.clearInputAfterSubmit
        : current.clearInputAfterSubmit,
    persistInputOnRestart:
      typeof importedRecord.persistInputOnRestart === 'boolean'
        ? imported.persistInputOnRestart
        : current.persistInputOnRestart,
    alwaysShowRetryButton:
      typeof importedRecord.alwaysShowRetryButton === 'boolean'
        ? imported.alwaysShowRetryButton
        : current.alwaysShowRetryButton,
  })
}

export const DEFAULT_SETTINGS: AppSettings = normalizeSettings({
  accessToken: '',
  baseUrl: DEFAULT_BASE_URL,
  apiKey: '',
  model: DEFAULT_IMAGES_MODEL,
  timeout: DEFAULT_API_TIMEOUT,
  apiMode: 'images',
  codexCli: true,
  apiProxy: DEFAULT_OPENAI_API_PROXY,
  clearInputAfterSubmit: true,
  persistInputOnRestart: true,
  alwaysShowRetryButton: false,
})
