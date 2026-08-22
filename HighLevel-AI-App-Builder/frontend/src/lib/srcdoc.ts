import bootstrapSource from '@/preview/bootstrap.js?raw'

/**
 * Assemble the sandboxed preview document from generated project files.
 * Local CSS/JS are inlined; remote <script>/<link> tags are preserved only
 * when they match the pinned CDN allowlist (which also matches the CSP).
 */

const CDN_ALLOWLIST = ['https://cdn.jsdelivr.net/']

const PREVIEW_CSP = [
  "default-src 'none'",
  // 'unsafe-eval' is required by Vue's runtime template compiler (the global
  // build compiles template strings via new Function). Inside this sandbox it
  // adds no exfiltration capability: the origin is opaque, 'unsafe-inline' is
  // already necessarily allowed (the code is untrusted by definition), and
  // connect-src 'none' + img-src data:/blob: remain the actual boundary.
  "script-src 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
  "style-src 'unsafe-inline' https://cdn.jsdelivr.net",
  'img-src data: blob:',
  'font-src https://cdn.jsdelivr.net',
  "connect-src 'none'",
  "form-action 'none'",
  "base-uri 'none'",
].join('; ')

function isAllowedRemote(url: string): boolean {
  return CDN_ALLOWLIST.some((prefix) => url.startsWith(prefix))
}

/** Escape `</script>` inside inlined code so it can't close our tag. */
function inlineScriptSafe(code: string): string {
  return code.replace(/<\/script/gi, '<\\/script')
}

function inlineStyleSafe(code: string): string {
  return code.replace(/<\/style/gi, '<\\/style')
}

export interface SrcdocResult {
  srcdoc: string
  warnings: string[]
}

export function assembleSrcdoc(files: ReadonlyMap<string, string>, parentOrigin: string): SrcdocResult {
  const warnings: string[] = []
  const indexHtml = files.get('index.html')
  if (!indexHtml) {
    return { srcdoc: emptyDocument('No index.html in this project yet.'), warnings }
  }

  const doc = new DOMParser().parseFromString(indexHtml, 'text/html')

  const title = doc.querySelector('title')?.textContent?.trim() || 'App preview'

  // Remote assets, in document order, filtered to the CDN allowlist.
  const remoteScripts: string[] = []
  const remoteStyles: string[] = []
  const localScriptPaths: string[] = []

  doc.querySelectorAll('script').forEach((el) => {
    const src = el.getAttribute('src')
    if (!src) {
      // Inline scripts inside generated index.html run as-is (rare).
      remoteScripts.push(`<script>${inlineScriptSafe(el.textContent ?? '')}</script>`)
      el.remove()
      return
    }
    if (isAllowedRemote(src)) {
      remoteScripts.push(`<script src="${src.replace(/"/g, '&quot;')}"></script>`)
    } else if (/^https?:/i.test(src)) {
      warnings.push(`Blocked non-allowlisted script: ${src}`)
    } else {
      localScriptPaths.push(normalizeRef(src))
    }
    el.remove()
  })

  doc.querySelectorAll('link[rel="stylesheet"]').forEach((el) => {
    const href = el.getAttribute('href')
    if (!href) return void el.remove()
    if (isAllowedRemote(href)) {
      remoteStyles.push(`<link rel="stylesheet" href="${href.replace(/"/g, '&quot;')}" />`)
    } else if (/^https?:/i.test(href)) {
      warnings.push(`Blocked non-allowlisted stylesheet: ${href}`)
    }
    el.remove()
  })

  // Inline every project stylesheet (referenced or not — order: referenced first).
  const cssPaths = [...files.keys()].filter((p) => p.endsWith('.css'))
  const styleBlocks = cssPaths.map(
    (p) => `<style data-path="${p}">\n${inlineStyleSafe(files.get(p) ?? '')}\n</style>`,
  )

  // Local scripts in reference order; warn on dangling refs.
  const scriptBlocks: string[] = []
  for (const path of localScriptPaths) {
    const content = files.get(path)
    if (content === undefined) {
      warnings.push(`index.html references missing file: ${path}`)
      continue
    }
    scriptBlocks.push(`<script data-path="${path}">\n${inlineScriptSafe(content)}\n</script>`)
  }

  const bootstrap = `<script>\n${inlineScriptSafe(
    // replaceAll: the token also appears in the bootstrap's doc comment.
    bootstrapSource.replaceAll('__GENESIS_PARENT_ORIGIN__', parentOrigin),
  )}\n</script>`

  const bodyInner = doc.body?.innerHTML ?? ''

  const srcdoc = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}" />
<title>${escapeHtml(title)}</title>
${bootstrap}
${remoteStyles.join('\n')}
${styleBlocks.join('\n')}
</head>
<body>
${bodyInner}
${remoteScripts.join('\n')}
${scriptBlocks.join('\n')}
</body>
</html>`

  return { srcdoc, warnings }
}

function normalizeRef(src: string): string {
  return src.replace(/^\.\//, '').replace(/^\//, '').split('?')[0]!
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function emptyDocument(message: string): string {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8" />
<meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}" />
<style>body{margin:0;display:grid;place-items:center;min-height:100vh;background:#121419;color:#99a0ad;font-family:system-ui,sans-serif;font-size:13px}</style>
</head><body><p>${escapeHtml(message)}</p></body></html>`
}
