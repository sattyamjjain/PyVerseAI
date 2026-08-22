/**
 * Incremental parser for the Genesis LLM output contract:
 *
 *   prose…
 *   <genApp id="kebab-id" title="Title">
 *   <genFile path="index.html">
 *   …verbatim file content…
 *   </genFile>
 *   <genDelete path="old.js"/>
 *   </genApp>
 *   prose…
 *
 * Design (chunk-fed state machine with a holdback buffer):
 *  - feed() is called once per model text delta; events fire as true deltas
 *    (no cumulative re-emits, O(n) total work).
 *  - While inside a file, everything except the last HOLD bytes of the buffer
 *    is provably content (HOLD = len("</genFile>") - 1), so a close marker
 *    split across chunks can never leak into emitted content.
 *  - A marker prefix at the end of the buffer waits for more data instead of
 *    being flushed, so tags split across chunks parse correctly.
 *  - finish() finalizes an unclosed file with truncated=true — the caller's
 *    signal to run a repair pass.
 */

import { MAX_FILE_BYTES, MAX_FILES_PER_PROJECT } from '../shared/paths.js'

const APP_OPEN = '<genApp'
const APP_CLOSE = '</genApp>'
const FILE_OPEN = '<genFile'
const FILE_CLOSE = '</genFile>'
const DELETE_OPEN = '<genDelete'
const HOLD = FILE_CLOSE.length - 1

export class GenParseError extends Error {
  constructor(
    readonly code: 'parse_failed' | 'file_too_large',
    message: string,
  ) {
    super(message)
  }
}

export interface GenParserHandlers {
  onNarrationDelta(text: string): void
  onAppStart(attrs: { id?: string; title?: string }): void
  onFileStart(path: string): void
  onFileDelta(path: string, content: string): void
  /**
   * content is the full assembled (and possibly normalized) file.
   * `changed` is true when normalization altered the streamed bytes — the
   * client should replace its buffer with this authoritative content.
   */
  onFileComplete(path: string, content: string, opts: { truncated: boolean; changed: boolean }): void
  onFileDeleted(path: string): void
  onAppEnd(): void
}

type State = 'TEXT' | 'IN_APP' | 'IN_FILE'

interface OpenTag {
  attrs: Record<string, string>
  /** Index just past the closing '>' of the open tag. */
  end: number
}

function parseAttrs(tag: string): Record<string, string> {
  const attrs: Record<string, string> = {}
  const re = /([a-zA-Z][a-zA-Z0-9_-]*)="([^"]*)"/g
  let m: RegExpExecArray | null
  while ((m = re.exec(tag)) !== null) attrs[m[1]!] = m[2]!
  return attrs
}

/**
 * Whole-content markdown-fence strip (anchored — mid-file fences preserved)
 * and defensive entity repair, applied at finalization only. The entity fix
 * runs only when the content contains no raw '<' at all (i.e. the model
 * escaped everything) so legitimate entities in real HTML are never touched.
 */
function finalizeContent(raw: string): string {
  let out = raw
  const fence = /^\s*```[\w-]*\n([\s\S]*?)\n\s*```\s*$/.exec(out)
  if (fence) out = fence[1]!
  if (!out.includes('<') && /&(lt|gt|amp);/.test(out)) {
    out = out.replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&')
  }
  if (out.length > 0 && !out.endsWith('\n')) out += '\n'
  return out
}

export class GenStreamParser {
  private buf = ''
  private state: State = 'TEXT'
  private currentPath: string | null = null
  private fileRaw = ''
  private fileCount = 0
  private appOpen = false
  private ended = false
  /** One newline directly after `<genFile …>` is formatting, not content —
   *  trimmed lazily because it may arrive in a later chunk. */
  private pendingLeadingTrim = false

  constructor(private readonly handlers: GenParserHandlers) {}

  feed(chunk: string): void {
    if (this.ended) return
    this.buf += chunk
    this.process()
  }

  /** Flush at end of stream (message_stop, abort, or provider error). */
  finish(): void {
    if (this.ended) return
    this.ended = true
    if (this.state === 'IN_FILE' && this.currentPath !== null) {
      if (this.buf.length > 0) {
        this.fileRaw += this.buf
        this.handlers.onFileDelta(this.currentPath, this.buf)
        this.buf = ''
      }
      const finalContent = finalizeContent(this.fileRaw)
      this.handlers.onFileComplete(this.currentPath, finalContent, {
        truncated: true,
        changed: finalContent !== this.fileRaw,
      })
      this.currentPath = null
      this.state = this.appOpen ? 'IN_APP' : 'TEXT'
    } else if (this.state === 'TEXT' && this.buf.length > 0) {
      this.handlers.onNarrationDelta(this.buf)
      this.buf = ''
    }
    if (this.appOpen) {
      this.appOpen = false
      this.handlers.onAppEnd()
    }
  }

  // ── internals ──────────────────────────────────────────────────────────────

  private process(): void {
    for (;;) {
      if (this.state === 'IN_FILE') {
        if (!this.processInFile()) return
      } else {
        if (!this.processTextOrApp()) return
      }
    }
  }

  /** Returns false when more data is needed (loop should stop). */
  private processInFile(): boolean {
    if (this.pendingLeadingTrim) {
      if (this.buf.length === 0 || this.buf === '\r') return false // wait for data
      if (this.buf.startsWith('\r\n')) this.buf = this.buf.slice(2)
      else if (this.buf.startsWith('\n')) this.buf = this.buf.slice(1)
      this.pendingLeadingTrim = false
    }
    const path = this.currentPath!
    const idx = this.buf.indexOf(FILE_CLOSE)
    if (idx !== -1) {
      const content = this.buf.slice(0, idx)
      if (content.length > 0) {
        this.fileRaw += content
        this.guardFileSize(path)
        this.handlers.onFileDelta(path, content)
      }
      const finalContent = finalizeContent(this.fileRaw)
      this.handlers.onFileComplete(path, finalContent, {
        truncated: false,
        changed: finalContent !== this.fileRaw,
      })
      this.buf = this.buf.slice(idx + FILE_CLOSE.length)
      this.currentPath = null
      this.fileRaw = ''
      this.state = this.appOpen ? 'IN_APP' : 'TEXT'
      return true
    }
    const safe = this.buf.length - HOLD
    if (safe > 0) {
      const content = this.buf.slice(0, safe)
      this.fileRaw += content
      this.guardFileSize(path)
      this.buf = this.buf.slice(safe)
      this.handlers.onFileDelta(path, content)
    }
    return false
  }

  private guardFileSize(path: string): void {
    if (this.fileRaw.length > MAX_FILE_BYTES) {
      throw new GenParseError('file_too_large', `${path} exceeded ${MAX_FILE_BYTES} bytes`)
    }
  }

  /** TEXT and IN_APP share marker-scanning logic; they differ in what happens
   *  to plain text (narration vs discarded) and which markers are live. */
  private processTextOrApp(): boolean {
    const inApp = this.state === 'IN_APP'
    const lt = this.buf.indexOf('<')

    if (lt === -1) {
      if (this.buf.length > 0 && !inApp) this.handlers.onNarrationDelta(this.buf)
      this.buf = ''
      return false
    }
    if (lt > 0) {
      const text = this.buf.slice(0, lt)
      if (!inApp) this.handlers.onNarrationDelta(text)
      this.buf = this.buf.slice(lt)
    }

    // buf now starts with '<'. Candidate markers for this state:
    const candidates = inApp
      ? [FILE_OPEN, DELETE_OPEN, APP_CLOSE]
      : [APP_OPEN, FILE_OPEN, DELETE_OPEN] // tolerate a missing <genApp> wrapper

    let matched: string | null = null
    let possiblePrefix = false
    for (const marker of candidates) {
      if (this.buf.startsWith(marker)) {
        // Guard against e.g. "<genApple": the char after the tag name must
        // terminate it. If the buffer ends exactly at the marker, wait.
        if (this.buf.length === marker.length) {
          possiblePrefix = true
          break
        }
        const next = this.buf[marker.length]!
        if (marker === APP_CLOSE || next === ' ' || next === '>' || next === '\n' || next === '\t' || next === '/') {
          matched = marker
          break
        }
      } else if (marker.startsWith(this.buf)) {
        possiblePrefix = true
      }
    }

    if (matched === null) {
      if (possiblePrefix) return false // partial marker at buffer end — wait
      // Ordinary '<' in prose (or stray char inside the app block).
      if (!inApp) this.handlers.onNarrationDelta('<')
      this.buf = this.buf.slice(1)
      return true
    }

    if (matched === APP_CLOSE) {
      this.buf = this.buf.slice(APP_CLOSE.length)
      this.appOpen = false
      this.state = 'TEXT'
      this.handlers.onAppEnd()
      return true
    }

    const tag = this.readOpenTag()
    if (tag === null) return false // open tag incomplete — wait

    if (matched === APP_OPEN) {
      this.buf = this.buf.slice(tag.end)
      this.appOpen = true
      this.state = 'IN_APP'
      this.handlers.onAppStart({ id: tag.attrs['id'], title: tag.attrs['title'] })
      return true
    }

    if (matched === DELETE_OPEN) {
      this.buf = this.buf.slice(tag.end)
      const path = tag.attrs['path']
      if (!path) throw new GenParseError('parse_failed', '<genDelete> missing path attribute')
      this.handlers.onFileDeleted(path)
      return true
    }

    // FILE_OPEN
    if (!this.appOpen) {
      // Implicit app wrapper for resilience.
      this.appOpen = true
      this.handlers.onAppStart({})
    }
    const path = tag.attrs['path']
    if (!path) throw new GenParseError('parse_failed', '<genFile> missing path attribute')
    this.fileCount += 1
    if (this.fileCount > MAX_FILES_PER_PROJECT) {
      throw new GenParseError('parse_failed', `more than ${MAX_FILES_PER_PROJECT} files in one generation`)
    }
    this.buf = this.buf.slice(tag.end)
    this.pendingLeadingTrim = true
    this.currentPath = path
    this.fileRaw = ''
    this.state = 'IN_FILE'
    this.handlers.onFileStart(path)
    return true
  }

  /** Parse an open tag from the start of buf; null if its '>' hasn't arrived. */
  private readOpenTag(): OpenTag | null {
    const gt = this.buf.indexOf('>')
    if (gt === -1) return null
    const tag = this.buf.slice(0, gt + 1)
    return { attrs: parseAttrs(tag), end: gt + 1 }
  }
}
