import { describe, expect, it } from 'vitest'
import { buildUpstreamUrl, matchAllowlist } from '../src/shared/allowlist.js'

const LOC = 'myLocation123'

describe('matchAllowlist', () => {
  it('matches list contacts with trailing slash', () => {
    const m = matchAllowlist('GET', '/contacts/')
    expect(m?.rule.pattern).toBe('/contacts/')
  })

  it('distinguishes /contacts/ (list) from /contacts/:id (get)', () => {
    const m = matchAllowlist('GET', '/contacts/abc123')
    expect(m?.rule.pattern).toBe('/contacts/:contactId')
    expect(m?.pathParams.contactId).toBe('abc123')
  })

  it('rejects unknown routes and wrong methods', () => {
    expect(matchAllowlist('GET', '/users/')).toBeNull()
    expect(matchAllowlist('DELETE', '/contacts/abc')).toBeNull()
    expect(matchAllowlist('POST', '/contacts/abc123')).toBeNull()
    expect(matchAllowlist('GET', '/oauth/token')).toBeNull()
  })

  it('rejects path traversal in every encoding', () => {
    expect(matchAllowlist('GET', '/contacts/../oauth/token')).toBeNull()
    expect(matchAllowlist('GET', '/contacts/%2e%2e/oauth/token')).toBeNull()
    expect(matchAllowlist('GET', '/contacts/%252e%252e/token')).toBeNull()
    expect(matchAllowlist('GET', '/contacts//search')).toBeNull()
    expect(matchAllowlist('GET', '\\contacts\\search')).toBeNull()
    expect(matchAllowlist('GET', '/contacts/a?x=1')).toBeNull()
    expect(matchAllowlist('GET', '/contacts/a#frag')).toBeNull()
  })

  it('rejects hostile path params', () => {
    expect(matchAllowlist('GET', '/contacts/<script>')).toBeNull()
    expect(matchAllowlist('GET', '/contacts/a b')).toBeNull()
    expect(matchAllowlist('GET', `/contacts/${'x'.repeat(80)}`)).toBeNull()
  })

  it('matches nested message + calendar routes', () => {
    expect(matchAllowlist('GET', '/conversations/c1/messages')?.rule.pattern).toBe(
      '/conversations/:conversationId/messages',
    )
    expect(matchAllowlist('GET', '/calendars/cal1/free-slots')?.rule.pattern).toBe(
      '/calendars/:calendarId/free-slots',
    )
    expect(matchAllowlist('POST', '/calendars/events/appointments')?.rule.requiresConfirm).toBe(true)
  })
})

describe('buildUpstreamUrl', () => {
  it('copies only allowlisted query keys and forces locationId last', () => {
    const m = matchAllowlist('GET', '/contacts/')!
    const url = buildUpstreamUrl(
      m,
      { limit: 20, query: 'john', locationId: 'ATTACKER', evil: 'x' },
      LOC,
    )
    expect(url.origin).toBe('https://services.leadconnectorhq.com')
    expect(url.searchParams.get('limit')).toBe('20')
    expect(url.searchParams.get('query')).toBe('john')
    expect(url.searchParams.get('evil')).toBeNull()
    expect(url.searchParams.getAll('locationId')).toEqual([LOC])
  })

  it('pins /locations/:locationId to the caller regardless of input', () => {
    const m = matchAllowlist('GET', '/locations/SOMEONE_ELSE')!
    const url = buildUpstreamUrl(m, undefined, LOC)
    expect(url.pathname).toBe(`/locations/${LOC}`)
  })

  it('escapes path params when rebuilding', () => {
    const m = matchAllowlist('GET', '/contacts/abc_DEF-123')!
    const url = buildUpstreamUrl(m, undefined, LOC)
    expect(url.pathname).toBe('/contacts/abc_DEF-123')
  })

  it('supports the /locations/me placeholder used by the SDK', () => {
    const m = matchAllowlist('GET', '/locations/me')!
    const url = buildUpstreamUrl(m, undefined, LOC)
    expect(url.pathname).toBe(`/locations/${LOC}`)
  })
})
