/**
 * Validation for LLM-produced project file paths and size limits.
 * Shared between the generation pipeline (server) and the SPA (rendering,
 * preview assembly). Dependency-free.
 */

export const MAX_FILES_PER_PROJECT = 40
export const MAX_FILE_BYTES = 200_000
export const MAX_PATH_LENGTH = 200
export const MAX_PATH_DEPTH = 4

const ALLOWED_EXTENSIONS = new Set(['html', 'css', 'js', 'json', 'svg'])
const WHOLE_PATH_RE = /^[a-zA-Z0-9_\-./]+$/
const SEGMENT_RE = /^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9]+)?$/
const FORBIDDEN_SEGMENTS = new Set(['__proto__', 'constructor', 'prototype'])

export interface PathValidation {
  ok: boolean
  reason?: string
}

export function validateFilePath(path: string): PathValidation {
  if (typeof path !== 'string' || path.length === 0) return { ok: false, reason: 'empty path' }
  if (path.length > MAX_PATH_LENGTH) return { ok: false, reason: 'path too long' }
  if (!WHOLE_PATH_RE.test(path)) return { ok: false, reason: 'illegal characters' }
  if (path.startsWith('/') || path.startsWith('.')) {
    return { ok: false, reason: 'must be a relative path' }
  }
  if (path.includes('..')) return { ok: false, reason: 'traversal not allowed' }
  if (path.includes('//')) return { ok: false, reason: 'empty segment' }

  const segments = path.split('/')
  if (segments.length > MAX_PATH_DEPTH) return { ok: false, reason: 'too deeply nested' }
  for (const seg of segments) {
    if (!SEGMENT_RE.test(seg)) return { ok: false, reason: `bad segment "${seg}"` }
    if (FORBIDDEN_SEGMENTS.has(seg.split('.')[0]!)) {
      return { ok: false, reason: 'forbidden segment name' }
    }
  }
  const ext = path.split('.').pop()!.toLowerCase()
  if (!ALLOWED_EXTENSIONS.has(ext)) return { ok: false, reason: `extension .${ext} not allowed` }
  return { ok: true }
}
