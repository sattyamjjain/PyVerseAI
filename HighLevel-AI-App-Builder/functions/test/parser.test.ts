import { describe, expect, it } from 'vitest'
import { GenStreamParser, GenParseError, type GenParserHandlers } from '../src/genesis/parser.js'

interface Collected {
  narration: string
  apps: Array<{ id?: string; title?: string }>
  fileStarts: string[]
  deltas: Record<string, string>
  completes: Array<{ path: string; content: string; truncated: boolean; changed: boolean }>
  deleted: string[]
  appEnds: number
}

function collect(): { handlers: GenParserHandlers; c: Collected } {
  const c: Collected = {
    narration: '',
    apps: [],
    fileStarts: [],
    deltas: {},
    completes: [],
    deleted: [],
    appEnds: 0,
  }
  const handlers: GenParserHandlers = {
    onNarrationDelta: (t) => (c.narration += t),
    onAppStart: (a) => c.apps.push(a),
    onFileStart: (p) => {
      c.fileStarts.push(p)
      c.deltas[p] = ''
    },
    onFileDelta: (p, t) => (c.deltas[p] = (c.deltas[p] ?? '') + t),
    onFileComplete: (path, content, { truncated, changed }) =>
      c.completes.push({ path, content, truncated, changed }),
    onFileDeleted: (p) => c.deleted.push(p),
    onAppEnd: () => c.appEnds++,
  }
  return { handlers, c }
}

const SAMPLE = `I'll build a tiny app with two files.

<genApp id="demo-app" title="Demo App">
<genFile path="index.html">
<!DOCTYPE html>
<html>
<body><div id="app">x < y is fine</div></body>
</html>
</genFile>
<genFile path="app.js">
const a = 1;
console.log(a < 2);
</genFile>
</genApp>

Done — created index.html and app.js.`

function run(text: string, chunkSize: number | 'whole'): Collected {
  const { handlers, c } = collect()
  const p = new GenStreamParser(handlers)
  if (chunkSize === 'whole') {
    p.feed(text)
  } else {
    for (let i = 0; i < text.length; i += chunkSize) p.feed(text.slice(i, i + chunkSize))
  }
  p.finish()
  return c
}

describe('GenStreamParser', () => {
  it('parses a complete response fed as one chunk', () => {
    const c = run(SAMPLE, 'whole')
    expect(c.apps).toEqual([{ id: 'demo-app', title: 'Demo App' }])
    expect(c.fileStarts).toEqual(['index.html', 'app.js'])
    expect(c.completes).toHaveLength(2)
    expect(c.completes[0]!.content).toContain('x < y is fine')
    expect(c.completes[0]!.truncated).toBe(false)
    expect(c.completes[1]!.content).toBe('const a = 1;\nconsole.log(a < 2);\n')
    expect(c.narration).toContain("I'll build a tiny app")
    expect(c.narration).toContain('Done — created')
    expect(c.narration).not.toContain('genFile')
    expect(c.appEnds).toBe(1)
  })

  it('produces identical results fed one byte at a time', () => {
    const whole = run(SAMPLE, 'whole')
    const byByte = run(SAMPLE, 1)
    expect(byByte.completes).toEqual(whole.completes)
    expect(byByte.narration).toBe(whole.narration)
    expect(byByte.fileStarts).toEqual(whole.fileStarts)
  })

  it('produces identical results across random chunk boundaries (fuzz)', () => {
    const whole = run(SAMPLE, 'whole')
    let seed = 42
    const rand = () => (seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31
    for (let round = 0; round < 25; round++) {
      const { handlers, c } = collect()
      const p = new GenStreamParser(handlers)
      let i = 0
      while (i < SAMPLE.length) {
        const n = 1 + Math.floor(rand() * 17)
        p.feed(SAMPLE.slice(i, i + n))
        i += n
      }
      p.finish()
      expect(c.completes).toEqual(whole.completes)
      expect(c.narration).toBe(whole.narration)
    }
  })

  it('streamed deltas assemble to the raw file content', () => {
    const c = run(SAMPLE, 3)
    expect(c.deltas['app.js']).toBe('const a = 1;\nconsole.log(a < 2);\n')
    // raw already ends with newline, so finalization changes nothing
    expect(c.completes[1]!.content).toBe(c.deltas['app.js'])
    expect(c.completes[1]!.changed).toBe(false)
  })

  it('keeps markdown code fences that appear inside file content', () => {
    const text = `<genApp id="a" title="t">
<genFile path="readme-widget.js">
const snippet = \`\`\`js
const x = 1
\`\`\`;
</genFile>
</genApp>`
    const c = run(text, 5)
    expect(c.completes[0]!.content).toContain('```js')
  })

  it('strips a whole-content markdown fence and reports changed', () => {
    const text = '<genFile path="app.js">\n```js\nconst x = 1;\n```\n</genFile>'
    const c = run(text, 'whole')
    expect(c.completes[0]!.content).toBe('const x = 1;\n')
    expect(c.completes[0]!.changed).toBe(true)
  })

  it('repairs fully entity-escaped files and reports changed', () => {
    const text = '<genFile path="frag.html">\n&lt;div&gt;hello&lt;/div&gt;\n</genFile>'
    const c = run(text, 'whole')
    expect(c.completes[0]!.content).toBe('<div>hello</div>\n')
    expect(c.completes[0]!.changed).toBe(true)
  })

  it('leaves legitimate entities alone when raw < is present', () => {
    const text = '<genFile path="page.html">\n<p>5 &lt; 6</p>\n</genFile>'
    const c = run(text, 'whole')
    expect(c.completes[0]!.content).toBe('<p>5 &lt; 6</p>\n')
  })

  it('finalizes an unclosed file at finish() with truncated=true', () => {
    const text = '<genApp id="a" title="t">\n<genFile path="app.js">\nconst x = 1;'
    const c = run(text, 4)
    expect(c.completes).toHaveLength(1)
    expect(c.completes[0]!.truncated).toBe(true)
    expect(c.completes[0]!.content).toBe('const x = 1;\n')
    expect(c.appEnds).toBe(1)
  })

  it('parses <genDelete path="..."/> self-closing tags', () => {
    const text = '<genApp id="a" title="t">\n<genDelete path="old.js"/>\n</genApp>'
    const c = run(text, 2)
    expect(c.deleted).toEqual(['old.js'])
  })

  it('tolerates a missing <genApp> wrapper (implicit app)', () => {
    const text = 'Plan.\n<genFile path="index.html">\n<p>hi</p>\n</genFile>\nDone.'
    const c = run(text, 6)
    expect(c.apps).toEqual([{}])
    expect(c.completes[0]!.path).toBe('index.html')
    expect(c.appEnds).toBe(1)
  })

  it('treats markers-with-suffix like <genApple as prose', () => {
    const c = run('An <genApple> is not a marker.', 3)
    expect(c.narration).toBe('An <genApple> is not a marker.')
    expect(c.apps).toHaveLength(0)
  })

  it('keeps ordinary angle brackets in narration', () => {
    const c = run('use x < y, and 3 > 2, done', 2)
    expect(c.narration).toBe('use x < y, and 3 > 2, done')
  })

  it('throws GenParseError on oversized files', () => {
    const { handlers } = collect()
    const p = new GenStreamParser(handlers)
    p.feed('<genFile path="big.js">\n')
    expect(() => {
      for (let i = 0; i < 300; i++) p.feed('x'.repeat(1000))
    }).toThrow(GenParseError)
  })

  it('throws GenParseError when a genFile has no path', () => {
    const { handlers } = collect()
    const p = new GenStreamParser(handlers)
    expect(() => p.feed('<genFile id="nope">\ncontent\n</genFile>')).toThrow(GenParseError)
  })

  it('handles a stray < at the very end of the stream', () => {
    const c = run('unbalanced <', 'whole')
    expect(c.narration).toBe('unbalanced <')
  })
})
