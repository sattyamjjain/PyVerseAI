import { describe, expect, it } from 'vitest'
import { validateFilePath } from '../src/shared/paths.js'

describe('validateFilePath', () => {
  it('accepts normal project paths', () => {
    expect(validateFilePath('index.html').ok).toBe(true)
    expect(validateFilePath('styles.css').ok).toBe(true)
    expect(validateFilePath('app.js').ok).toBe(true)
    expect(validateFilePath('lib/utils.js').ok).toBe(true)
    expect(validateFilePath('assets/icons/logo.svg').ok).toBe(true)
  })

  it('rejects traversal and absolute paths', () => {
    expect(validateFilePath('../evil.js').ok).toBe(false)
    expect(validateFilePath('/etc/passwd').ok).toBe(false)
    expect(validateFilePath('a/../b.js').ok).toBe(false)
    expect(validateFilePath('.hidden.js').ok).toBe(false)
  })

  it('rejects disallowed extensions and weird names', () => {
    expect(validateFilePath('shell.sh').ok).toBe(false)
    expect(validateFilePath('page.php').ok).toBe(false)
    expect(validateFilePath('noext').ok).toBe(false)
    expect(validateFilePath('a//b.js').ok).toBe(false)
    expect(validateFilePath('sp ace.js').ok).toBe(false)
  })

  it('rejects prototype-pollution segment names', () => {
    expect(validateFilePath('__proto__/x.js').ok).toBe(false)
    expect(validateFilePath('constructor.js').ok).toBe(false)
    expect(validateFilePath('prototype/app.js').ok).toBe(false)
  })

  it('enforces depth and length limits', () => {
    expect(validateFilePath('a/b/c/d/e.js').ok).toBe(false) // depth 5
    expect(validateFilePath('a/b/c/d.js').ok).toBe(true) // depth 4
    expect(validateFilePath('x'.repeat(210) + '.js').ok).toBe(false)
  })
})
