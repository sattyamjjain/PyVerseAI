import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePreviewStore } from '@/stores/preview'

const ORIGIN = 'https://genesis.example.com'

function builtStore() {
  const preview = usePreviewStore()
  preview.rebuild(
    new Map([['index.html', '<html><body><h1>Old project</h1></body></html>']]),
    ORIGIN,
  )
  return preview
}

describe('preview store reset', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('clears the built srcdoc so a project switch cannot flash the previous app', () => {
    const preview = builtStore()
    expect(preview.hasBuilt).toBe(true)
    expect(preview.srcdoc).toContain('Old project')

    preview.reset()

    expect(preview.srcdoc).toBe('')
    expect(preview.hasBuilt).toBe(false)
    expect(preview.ready).toBe(false)
    expect(preview.updating).toBe(false)
  })

  it('bumps srcdocKey on reset so a mounted iframe is torn down', () => {
    const preview = builtStore()
    const key = preview.srcdocKey
    preview.reset()
    expect(preview.srcdocKey).toBe(key + 1)
  })

  it('clears per-project console, warnings, and runtime error state', () => {
    const preview = builtStore()
    preview.onPreviewMessage({ v: 1, type: 'preview.console', level: 'error', args: ['boom'] })
    preview.onPreviewMessage({ v: 1, type: 'preview.error', message: 'ReferenceError: x' })
    preview.consoleOpen = true
    expect(preview.consoleEntries.length).toBeGreaterThan(0)
    expect(preview.runtimeError).not.toBeNull()

    preview.reset()

    expect(preview.consoleEntries).toEqual([])
    expect(preview.warnings).toEqual([])
    expect(preview.runtimeError).toBeNull()
    expect(preview.consoleOpen).toBe(false)
    expect(preview.errorCount).toBe(0)
  })

  it('keeps deviceMode across resets (viewer preference, not project content)', () => {
    const preview = builtStore()
    preview.deviceMode = 'mobile'
    preview.reset()
    expect(preview.deviceMode).toBe('mobile')
  })
})
