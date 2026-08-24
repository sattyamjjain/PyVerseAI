import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { TsLike } from '@shared/models'
import { absoluteTime, formatDuration, relativeTime, toMillis } from '@/lib/time'

const NOW = new Date('2026-08-24T12:00:00Z').getTime()

function tsAt(ms: number): TsLike {
  return { toMillis: () => ms, toDate: () => new Date(ms) }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('toMillis', () => {
  it('returns 0 for missing timestamps and for timestamps whose toMillis throws', () => {
    expect(toMillis(undefined)).toBe(0)
    expect(toMillis(null)).toBe(0)
    // Structurally-typed TsLike: a malformed doc must degrade, not crash the UI.
    const broken = {
      toMillis: () => {
        throw new Error('not a Timestamp')
      },
      toDate: () => new Date(),
    }
    expect(toMillis(broken)).toBe(0)
    expect(toMillis(tsAt(1234))).toBe(1234)
  })
})

describe('relativeTime', () => {
  it('is empty for missing or zero timestamps', () => {
    expect(relativeTime(undefined)).toBe('')
    expect(relativeTime(null)).toBe('')
    expect(relativeTime(0)).toBe('')
  })

  it('buckets seconds, minutes, and hours with round-half boundaries', () => {
    expect(relativeTime(tsAt(NOW))).toBe('just now')
    expect(relativeTime(NOW - 44_999)).toBe('just now') // raw millis accepted too
    expect(relativeTime(NOW - 45_000)).toBe('1m ago')
    expect(relativeTime(NOW - 30 * 60_000)).toBe('30m ago')
    expect(relativeTime(NOW - 59 * 60_000)).toBe('59m ago')
    // 59m40s rounds to 60 minutes, which promotes to the hour bucket.
    expect(relativeTime(NOW - (59 * 60_000 + 40_000))).toBe('1h ago')
    expect(relativeTime(NOW - 23 * 3_600_000)).toBe('23h ago')
    // 23h40m rounds to 24h, which promotes to the day bucket.
    expect(relativeTime(NOW - (23 * 3_600_000 + 40 * 60_000))).toBe('1d ago')
  })

  it('shows day counts up to a week, then a short calendar date', () => {
    expect(relativeTime(NOW - 3 * 86_400_000)).toBe('3d ago')
    expect(relativeTime(NOW - 6 * 86_400_000)).toBe('6d ago')
    const dated = relativeTime(NOW - 10 * 86_400_000)
    expect(dated).not.toContain('ago')
    expect(dated).toMatch(/\d/) // locale short date, e.g. "Aug 14"
  })
})

describe('absoluteTime', () => {
  it('is empty for missing timestamps and renders a dated string otherwise', () => {
    expect(absoluteTime(undefined)).toBe('')
    expect(absoluteTime(null)).toBe('')
    expect(absoluteTime(0)).toBe('')
    expect(absoluteTime(tsAt(NOW))).toContain('2026')
  })
})

describe('formatDuration', () => {
  it('buckets sub-second, seconds, and minutes with rounding at the edges', () => {
    expect(formatDuration(0)).toBe('<1s')
    expect(formatDuration(999)).toBe('<1s')
    expect(formatDuration(1_000)).toBe('1s')
    expect(formatDuration(59_400)).toBe('59s')
    // 59.5s rounds to 60s, which promotes to the minute format.
    expect(formatDuration(59_500)).toBe('1m 0s')
    expect(formatDuration(90_000)).toBe('1m 30s')
    expect(formatDuration(605_000)).toBe('10m 5s')
  })
})
