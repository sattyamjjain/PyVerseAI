/** Line-level diff counts. Exact LCS under a size cap, fast heuristic above. */

const MAX_EXACT_LINES = 1500

export interface DiffCounts {
  added: number
  removed: number
}

export function lineDiffCounts(before: string, after: string): DiffCounts {
  if (before === after) return { added: 0, removed: 0 }
  const a = before.length ? before.split('\n') : []
  const b = after.length ? after.split('\n') : []
  if (a.length === 0) return { added: b.length, removed: 0 }
  if (b.length === 0) return { added: 0, removed: a.length }

  if (a.length > MAX_EXACT_LINES || b.length > MAX_EXACT_LINES) {
    // Multiset heuristic: unmatched lines on each side.
    const counts = new Map<string, number>()
    for (const line of a) counts.set(line, (counts.get(line) ?? 0) + 1)
    let common = 0
    for (const line of b) {
      const n = counts.get(line) ?? 0
      if (n > 0) {
        common++
        counts.set(line, n - 1)
      }
    }
    return { added: b.length - common, removed: a.length - common }
  }

  // LCS length via single-array DP.
  const prev = Array.from({ length: b.length + 1 }, () => 0)
  for (let i = 1; i <= a.length; i++) {
    let diag = 0
    for (let j = 1; j <= b.length; j++) {
      const tmp = prev[j]!
      prev[j] = a[i - 1] === b[j - 1] ? diag + 1 : Math.max(prev[j]!, prev[j - 1]!)
      diag = tmp
    }
  }
  const lcs = prev[b.length]!
  return { added: b.length - lcs, removed: a.length - lcs }
}

export type FileChangeStatus = 'A' | 'M' | 'D'

export interface FileChange {
  path: string
  status: FileChangeStatus
  added: number
  removed: number
  before: string
  after: string
}

/** Changed files between two {path → content} maps (unchanged omitted). */
export function computeChanges(
  before: ReadonlyMap<string, string>,
  after: ReadonlyMap<string, string>,
): FileChange[] {
  const changes: FileChange[] = []
  const paths = new Set([...before.keys(), ...after.keys()])
  for (const path of [...paths].sort()) {
    const b = before.get(path)
    const a = after.get(path)
    if (b === undefined && a !== undefined) {
      changes.push({ path, status: 'A', ...lineDiffCounts('', a), before: '', after: a })
    } else if (b !== undefined && a === undefined) {
      changes.push({ path, status: 'D', ...lineDiffCounts(b, ''), before: b, after: '' })
    } else if (b !== undefined && a !== undefined && b !== a) {
      changes.push({ path, status: 'M', ...lineDiffCounts(b, a), before: b, after: a })
    }
  }
  return changes
}
