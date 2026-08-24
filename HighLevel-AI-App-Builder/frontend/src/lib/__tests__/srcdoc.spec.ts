import { describe, expect, it } from 'vitest'
import { assembleSrcdoc } from '@/lib/srcdoc'

const ORIGIN = 'https://genesis.example.com'

function files(entries: Record<string, string>): Map<string, string> {
  return new Map(Object.entries(entries))
}

function assemble(entries: Record<string, string>) {
  return assembleSrcdoc(files(entries), ORIGIN)
}

describe('assembleSrcdoc', () => {
  it('renders a CSP-locked placeholder when index.html is missing', () => {
    const { srcdoc, warnings } = assemble({ 'app.js': 'x' })
    expect(srcdoc).toContain('No index.html in this project yet.')
    expect(srcdoc).toContain("connect-src 'none'")
    expect(warnings).toEqual([])
  })

  it('assembles bootstrap, styles, body markup, and scripts in that order', () => {
    const { srcdoc, warnings } = assemble({
      'index.html':
        '<html><head><title>Todo App</title><script src="./app.js"></script></head>' +
        '<body><div id="app">Hello</div></body></html>',
      'style.css': 'body { color: red }',
      'theme.css': ':root { --x: 1 }', // never referenced — still shipped
      'app.js': 'console.log("boot")',
    })

    expect(warnings).toEqual([])
    expect(srcdoc).toContain('<title>Todo App</title>')
    // Referenced and unreferenced stylesheets are both inlined.
    expect(srcdoc).toContain('<style data-path="style.css">')
    expect(srcdoc).toContain('<style data-path="theme.css">')
    expect(srcdoc).toContain('body { color: red }')

    const pos = (needle: string) => {
      const i = srcdoc.indexOf(needle)
      expect(i, `expected srcdoc to contain: ${needle}`).toBeGreaterThanOrEqual(0)
      return i
    }
    // Bootstrap must run before any project code; styles live in head;
    // project scripts execute after the body markup exists.
    expect(pos("var PARENT_ORIGIN = '")).toBeLessThan(pos('<style data-path="style.css">'))
    expect(pos('<style data-path="style.css">')).toBeLessThan(pos('<div id="app">Hello</div>'))
    expect(pos('<div id="app">Hello</div>')).toBeLessThan(pos('<script data-path="app.js">'))
    expect(pos('<script data-path="app.js">')).toBeLessThan(pos('console.log("boot")'))
  })

  it('replaces EVERY occurrence of the parent-origin placeholder (replaceAll regression)', () => {
    // The token appears twice in bootstrap.js — in a doc comment first, then in
    // the actual assignment. A single .replace() only fixed the comment and left
    // the assignment broken (real production bug).
    const { srcdoc } = assemble({ 'index.html': '<html><body></body></html>' })

    expect(srcdoc).not.toContain('__GENESIS_PARENT_ORIGIN__')
    expect(srcdoc).toContain(`var PARENT_ORIGIN = '${ORIGIN}'`)
    const occurrences = srcdoc.split(ORIGIN).length - 1
    expect(occurrences).toBeGreaterThanOrEqual(2)
  })

  it('embeds a CSP meta that denies network and non-CDN sources', () => {
    const { srcdoc } = assemble({ 'index.html': '<html><body></body></html>' })
    const match = srcdoc.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)"/)
    expect(match).not.toBeNull()
    const csp = match![1]!
    expect(csp).toContain("default-src 'none'")
    expect(csp).toContain("connect-src 'none'")
    expect(csp).toContain("form-action 'none'")
    expect(csp).toContain("base-uri 'none'")
    expect(csp).toContain("script-src 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net")
  })

  it('inlines local scripts in reference order and normalizes ./, /, and query refs', () => {
    const { srcdoc, warnings } = assemble({
      'index.html':
        '<html><head><script src="/second.js"></script><script src="./first.js?v=2"></script></head>' +
        '<body></body></html>',
      // Map insertion order is the reverse of reference order on purpose.
      'first.js': 'window.first = true',
      'second.js': 'window.second = true',
    })

    expect(warnings).toEqual([])
    const second = srcdoc.indexOf('<script data-path="second.js">')
    const first = srcdoc.indexOf('<script data-path="first.js">')
    expect(second).toBeGreaterThanOrEqual(0)
    expect(first).toBeGreaterThanOrEqual(0)
    expect(second).toBeLessThan(first) // document reference order wins over map order
  })

  it('escapes </script> inside inlined file content so it cannot break out', () => {
    // File contents are the untrusted path: they are inlined verbatim, unlike
    // inline scripts in index.html, which the HTML parser already terminates
    // at any embedded </script during DOMParser parsing.
    const { srcdoc } = assemble({
      'index.html':
        '<html><head><script src="./app.js"></script>' +
        '<script>window.inlined = 1</script></head><body></body></html>',
      'app.js': 'console.log("</script><img src=x>"); const s = "</ScRiPt>"',
    })
    expect(srcdoc).not.toContain('</script><img')
    expect(srcdoc).toContain('console.log("<\\/script><img src=x>")')
    // Mixed-case closers are matched case-insensitively (emitted lowercase).
    expect(srcdoc).not.toMatch(/<\/ScRiPt/)
    expect(srcdoc).toContain('const s = "<\\/script>"')
    expect(srcdoc).toContain('window.inlined = 1') // inline index.html scripts survive
  })

  it('keeps allowlisted CDN assets and blocks other remote URLs with warnings', () => {
    const { srcdoc, warnings } = assemble({
      'index.html':
        '<html><head>' +
        '<script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>' +
        '<script src="https://evil.example.com/x.js"></script>' +
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css">' +
        '<link rel="stylesheet" href="http://evil.example.com/y.css">' +
        '</head><body></body></html>',
    })

    expect(srcdoc).toContain('<script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js">')
    expect(srcdoc).toContain('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css" />')
    expect(srcdoc).not.toContain('evil.example.com')
    expect(warnings).toEqual([
      'Blocked non-allowlisted script: https://evil.example.com/x.js',
      'Blocked non-allowlisted stylesheet: http://evil.example.com/y.css',
    ])
  })

  it('warns about dangling local script references instead of emitting empty tags', () => {
    const { srcdoc, warnings } = assemble({
      'index.html': '<html><head><script src="./missing.js"></script></head><body></body></html>',
    })
    expect(warnings).toEqual(['index.html references missing file: missing.js'])
    expect(srcdoc).not.toContain('data-path="missing.js"')
  })

  it('escapes the document title and falls back when absent', () => {
    const escaped = assemble({
      'index.html': '<html><head><title>Ads & <Tags></title></head><body></body></html>',
    })
    expect(escaped.srcdoc).toContain('<title>Ads &amp; &lt;Tags&gt;</title>')

    const fallback = assemble({ 'index.html': '<html><body></body></html>' })
    expect(fallback.srcdoc).toContain('<title>App preview</title>')
  })
})
