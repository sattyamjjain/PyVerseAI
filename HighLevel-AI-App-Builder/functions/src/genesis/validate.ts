import { validateFilePath } from '../shared/paths.js'

export interface Violation {
  code: 'bad_path' | 'egress' | 'forbidden_api' | 'secret_shape' | 'no_entry'
  path?: string
  detail: string
}

export interface ValidationWarning {
  code: 'missing_ref' | 'shrunk_file' | 'duplicate_path'
  path?: string
  detail: string
}

/** External URLs permitted inside generated code (pinned CDN only). */
const URL_ALLOWLIST = [
  /^https:\/\/cdn\.jsdelivr\.net\/npm\/vue@3(\.\d+){0,2}\/dist\/vue\.global\.prod\.js$/,
  // XML namespace identifiers (inline SVG xmlns attrs / data-URI icons) —
  // string identifiers, never fetched.
  /^https?:\/\/www\.w3\.org\//,
]

const URL_RE = /https?:\/\/[^\s"'<>)]+/g

const FORBIDDEN_PATTERNS: Array<{ re: RegExp; detail: string }> = [
  { re: /\beval\s*\(/, detail: 'eval() is not allowed' },
  { re: /\bnew\s+Function\s*\(/, detail: 'new Function() is not allowed' },
  { re: /document\.cookie/, detail: 'document.cookie access is not allowed' },
  { re: /window\.(parent|top)\b/, detail: 'window.parent/top access is not allowed' },
  { re: /\bXMLHttpRequest\b/, detail: 'XMLHttpRequest is not allowed (use the genesis SDK)' },
  { re: /\bnew\s+WebSocket\b/, detail: 'WebSocket is not allowed' },
  { re: /\bnew\s+EventSource\b/, detail: 'EventSource is not allowed' },
  { re: /navigator\.sendBeacon/, detail: 'sendBeacon is not allowed' },
  { re: /\bfetch\s*\(/, detail: 'fetch() is not allowed (use the genesis SDK)' },
]

const SECRET_SHAPES: Array<{ re: RegExp; detail: string }> = [
  { re: /sk-[A-Za-z0-9_-]{20,}/, detail: 'API-key-shaped string' },
  { re: /AIza[0-9A-Za-z_-]{35}/, detail: 'Google-API-key-shaped string' },
  { re: /Bearer\s+[A-Za-z0-9._-]{25,}/, detail: 'bearer-token-shaped string' },
  { re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/, detail: 'private key material' },
]

export interface GenerationValidation {
  violations: Violation[]
  warnings: ValidationWarning[]
}

/**
 * Post-stream validation. `written` are the files this generation produced;
 * `merged` is the full project state after applying writes + deletes.
 * Defense-in-depth tripwire — the sandbox CSP is the real boundary.
 */
export function validateGeneration(
  written: Array<{ path: string; content: string }>,
  merged: Map<string, string>,
  previous: Map<string, string>,
): GenerationValidation {
  const violations: Violation[] = []
  const warnings: ValidationWarning[] = []

  for (const f of written) {
    const pv = validateFilePath(f.path)
    if (!pv.ok) {
      violations.push({ code: 'bad_path', path: f.path, detail: pv.reason! })
      continue
    }
    for (const url of f.content.match(URL_RE) ?? []) {
      if (!URL_ALLOWLIST.some((re) => re.test(url))) {
        violations.push({ code: 'egress', path: f.path, detail: `external URL: ${url.slice(0, 120)}` })
      }
    }
    if (f.path.endsWith('.js') || f.path.endsWith('.html')) {
      for (const { re, detail } of FORBIDDEN_PATTERNS) {
        if (re.test(f.content)) violations.push({ code: 'forbidden_api', path: f.path, detail })
      }
    }
    for (const { re, detail } of SECRET_SHAPES) {
      if (re.test(f.content)) violations.push({ code: 'secret_shape', path: f.path, detail })
    }
    const prev = previous.get(f.path)
    if (prev && prev.length > 500 && f.content.length < prev.length * 0.2) {
      warnings.push({
        code: 'shrunk_file',
        path: f.path,
        detail: `rewritten file shrank ${prev.length}→${f.content.length} chars`,
      })
    }
  }

  if (!merged.has('index.html')) {
    violations.push({ code: 'no_entry', detail: 'project has no index.html entry point' })
  } else {
    const html = merged.get('index.html')!
    const refRe = /(?:src|href)="([^"]+)"/g
    let m: RegExpExecArray | null
    while ((m = refRe.exec(html)) !== null) {
      const ref = m[1]!
      if (/^(https?:|data:|#|mailto:|tel:)/.test(ref)) continue
      const normalized = ref.replace(/^\.\//, '')
      if (!merged.has(normalized)) {
        warnings.push({ code: 'missing_ref', path: normalized, detail: `index.html references missing file "${ref}"` })
      }
    }
  }

  return { violations, warnings }
}

/** Cheap line-level ± counts for snapshot badges (multiset diff, not LCS). */
export function lineDiffCounts(
  previous: Map<string, string>,
  next: Map<string, string>,
): { added: number; removed: number } {
  let added = 0
  let removed = 0
  const paths = new Set([...previous.keys(), ...next.keys()])
  for (const path of paths) {
    const oldLines = previous.get(path)?.split('\n') ?? []
    const newLines = next.get(path)?.split('\n') ?? []
    const counts = new Map<string, number>()
    for (const l of oldLines) counts.set(l, (counts.get(l) ?? 0) + 1)
    for (const l of newLines) {
      const c = counts.get(l) ?? 0
      if (c > 0) counts.set(l, c - 1)
      else added++
    }
    for (const c of counts.values()) removed += c
  }
  return { added, removed }
}
