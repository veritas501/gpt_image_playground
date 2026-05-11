import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { createPortal } from 'react-dom'
import { clearData, exportData, importData, useStore } from '../store'
import { useCloseOnEscape } from '../hooks/useCloseOnEscape'
import { usePreventBackgroundScroll } from '../hooks/usePreventBackgroundScroll'

interface SettingsModalProps {
  onClose?: () => void
}

export default function SettingsModal({ onClose }: SettingsModalProps) {
  const showSettings = useStore((s) => s.showSettings)
  const settings = useStore((s) => s.settings)
  const setSettings = useStore((s) => s.setSettings)
  const setShowSettings = useStore((s) => s.setShowSettings)
  const showToast = useStore((s) => s.showToast)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isClearing, setIsClearing] = useState(false)

  const close = () => {
    setShowSettings(false)
    onClose?.()
  }

  useCloseOnEscape(showSettings, close)
  usePreventBackgroundScroll(showSettings)

  if (!showSettings) return null

  const handleExport = async () => {
    setIsExporting(true)
    try {
      await exportData({ exportConfig: true, exportTasks: false })
      showToast('已导出前端设置', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : '导出失败', 'error')
    } finally {
      setIsExporting(false)
    }
  }

  const handleImport = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setIsImporting(true)
    try {
      const imported = await importData(file, { importConfig: true, importTasks: false })
      if (imported) showToast('已导入前端设置', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : '导入失败', 'error')
    } finally {
      setIsImporting(false)
    }
  }

  const handleClearTasks = async () => {
    setIsClearing(true)
    try {
      await clearData({ clearConfig: false, clearTasks: true })
      showToast('已清空任务与图片缓存', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : '清空失败', 'error')
    } finally {
      setIsClearing(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center bg-black/55 backdrop-blur-sm">
      <div
        className="absolute inset-0"
        onClick={close}
      />
      <section className="relative z-10 w-full max-w-2xl rounded-t-3xl sm:rounded-3xl border border-white/10 bg-white shadow-2xl sm:max-h-[85vh] overflow-y-auto dark:bg-gray-950">
        <header className="flex items-center justify-between px-6 py-5 border-b border-gray-200 dark:border-white/10">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">应用设置</h2>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              当前前端只连接本站后端，不再暴露上游 API Key、Provider 和上游地址。
            </p>
          </div>
          <button
            type="button"
            onClick={close}
            className="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-white/10"
          >
            关闭
          </button>
        </header>

        <div className="space-y-6 px-6 py-6">
          <section className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">访问口令</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                每次请求都会通过 `X-Access-Token` 发送到后端，由后端再调用内网上游。
              </p>
            </div>
            <input
              type="password"
              value={settings.accessToken}
              onChange={(event) => setSettings({ accessToken: event.target.value })}
              placeholder="输入后端访问口令"
              className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-gray-900 dark:border-white/15 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-white/40"
            />
          </section>

          <section className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">本地行为</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                这里只保留前端本地体验相关设置，不再维护上游连接配置。
              </p>
            </div>
            <label className="flex items-start gap-3 rounded-2xl border border-gray-200 p-4 dark:border-white/10">
              <input
                type="checkbox"
                checked={settings.clearInputAfterSubmit}
                onChange={(event) => setSettings({ clearInputAfterSubmit: event.target.checked })}
                className="mt-1 h-4 w-4 rounded border-gray-300"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900 dark:text-gray-100">提交后清空输入</span>
                <span className="block text-sm text-gray-500 dark:text-gray-400">适合连续批量提交时减少手动清理。</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-2xl border border-gray-200 p-4 dark:border-white/10">
              <input
                type="checkbox"
                checked={settings.persistInputOnRestart}
                onChange={(event) => setSettings({ persistInputOnRestart: event.target.checked })}
                className="mt-1 h-4 w-4 rounded border-gray-300"
              />
              <span>
                <span className="block text-sm font-medium text-gray-900 dark:text-gray-100">刷新后保留输入区内容</span>
                <span className="block text-sm text-gray-500 dark:text-gray-400">仅影响本地输入草稿，不影响后端任务持久化。</span>
              </span>
            </label>
          </section>

          <section className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">数据维护</h3>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                这里只导入导出前端设置；任务与图片始终以后端为准，本地只保留缓存。
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleExport}
                disabled={isExporting}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-900 hover:bg-gray-100 disabled:opacity-60 dark:border-white/15 dark:text-gray-100 dark:hover:bg-white/10"
              >
                {isExporting ? '导出中...' : '导出前端设置'}
              </button>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isImporting}
                className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-900 hover:bg-gray-100 disabled:opacity-60 dark:border-white/15 dark:text-gray-100 dark:hover:bg-white/10"
              >
                {isImporting ? '导入中...' : '导入前端设置'}
              </button>
              <button
                type="button"
                onClick={handleClearTasks}
                disabled={isClearing}
                className="rounded-xl border border-red-300 px-4 py-2 text-sm text-red-700 hover:bg-red-50 disabled:opacity-60 dark:border-red-500/30 dark:text-red-300 dark:hover:bg-red-500/10"
              >
                {isClearing ? '清空中...' : '清空本地缓存'}
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.json,application/zip,application/json"
              onChange={handleImport}
              className="hidden"
            />
          </section>
        </div>
      </section>
    </div>,
    document.body,
  )
}
