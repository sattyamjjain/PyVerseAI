import type { TsLike } from '@shared/models'

export function toMillis(ts: TsLike | undefined | null): number {
  if (!ts) return 0
  try {
    return ts.toMillis()
  } catch {
    return 0
  }
}

/** "just now", "4m ago", "2h ago", "3d ago", else a short date. */
export function relativeTime(ts: TsLike | number | undefined | null): string {
  const ms = typeof ts === 'number' ? ts : toMillis(ts)
  if (!ms) return ''
  const diff = Date.now() - ms
  if (diff < 45_000) return 'just now'
  const mins = Math.round(diff / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function absoluteTime(ts: TsLike | number | undefined | null): string {
  const ms = typeof ts === 'number' ? ts : toMillis(ts)
  if (!ms) return ''
  return new Date(ms).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return '<1s'
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return `${m}m ${s % 60}s`
}
