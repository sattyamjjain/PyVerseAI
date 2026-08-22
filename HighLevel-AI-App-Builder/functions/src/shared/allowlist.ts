/**
 * The HighLevel endpoint allowlist — the single source of truth used by BOTH
 * the hlProxy Cloud Function (enforcement) and the SPA's preview bridge
 * (pre-validation + write-confirmation UX). Dependency-free by design.
 *
 * Security invariants (see README security notes):
 *  - The upstream URL is always rebuilt from OUR pattern template; the client
 *    string is only ever segment-matched, never concatenated.
 *  - locationId is forced from the caller's stored connection AFTER copying
 *    allowlisted query keys, so a client-supplied locationId can never win.
 *  - Write routes carry `requiresConfirm`: the parent app shows an
 *    unspoofable confirmation dialog before forwarding them.
 */

export interface AllowRule {
  method: 'GET' | 'POST' | 'PUT'
  /** Path template; `:name` segments match a single safe path segment. */
  pattern: string
  /** Query keys copied through from the client (locationId is always server-set). */
  allowedQuery?: readonly string[]
  /** True when the route accepts a locationId query param the server must set. */
  locationIdInQuery?: boolean
  /** True when the route accepts a JSON body whose locationId the server must overwrite. */
  locationIdInBody?: boolean
  /** Writes require an explicit user confirmation in the parent app. */
  requiresConfirm?: boolean
  /** Short human label used by the confirmation dialog ("Create a contact"). */
  label: string
}

export const HL_API_BASE = 'https://services.leadconnectorhq.com'

/**
 * Version header is pinned per API family (a top source of confusing 4xxs):
 * Contacts + Locations → 2021-07-28; Conversations + Calendars → 2021-04-15.
 */
export function hlVersionFor(path: string): string {
  if (path.startsWith('/conversations') || path.startsWith('/calendars')) return '2021-04-15'
  return '2021-07-28'
}

export const HL_ALLOWLIST: readonly AllowRule[] = [
  // ── Contacts ──────────────────────────────────────────────────────────────
  {
    method: 'GET',
    pattern: '/contacts/',
    allowedQuery: ['limit', 'startAfter', 'startAfterId', 'query'],
    locationIdInQuery: true,
    label: 'List contacts',
  },
  {
    method: 'POST',
    pattern: '/contacts/search',
    locationIdInBody: true,
    label: 'Search contacts',
  },
  { method: 'GET', pattern: '/contacts/:contactId', label: 'Get a contact' },
  {
    method: 'POST',
    pattern: '/contacts/',
    locationIdInBody: true,
    requiresConfirm: true,
    label: 'Create a contact',
  },
  {
    method: 'PUT',
    pattern: '/contacts/:contactId',
    requiresConfirm: true,
    label: 'Update a contact',
  },

  // ── Conversations ─────────────────────────────────────────────────────────
  {
    method: 'GET',
    pattern: '/conversations/search',
    allowedQuery: ['limit', 'status', 'sortBy', 'sort', 'contactId', 'query', 'startAfterDate'],
    locationIdInQuery: true,
    label: 'List conversations',
  },
  { method: 'GET', pattern: '/conversations/:conversationId', label: 'Get a conversation' },
  {
    method: 'GET',
    pattern: '/conversations/:conversationId/messages',
    allowedQuery: ['limit', 'lastMessageId', 'type'],
    label: 'Get messages',
  },
  {
    method: 'POST',
    pattern: '/conversations/messages',
    requiresConfirm: true,
    label: 'Send a message',
  },

  // ── Calendars ─────────────────────────────────────────────────────────────
  {
    method: 'GET',
    pattern: '/calendars/',
    allowedQuery: ['groupId', 'showDrafted'],
    locationIdInQuery: true,
    label: 'List calendars',
  },
  {
    method: 'GET',
    pattern: '/calendars/events',
    // HighLevel requires exactly one of calendarId | userId | groupId besides
    // locationId + the epoch-millisecond startTime/endTime window.
    allowedQuery: ['calendarId', 'userId', 'groupId', 'startTime', 'endTime'],
    locationIdInQuery: true,
    label: 'List appointments',
  },
  { method: 'GET', pattern: '/calendars/events/appointments/:eventId', label: 'Get an appointment' },
  {
    method: 'GET',
    pattern: '/calendars/:calendarId/free-slots',
    allowedQuery: ['startDate', 'endDate', 'timezone', 'userId'],
    label: 'Get free slots',
  },
  {
    method: 'POST',
    pattern: '/calendars/events/appointments',
    locationIdInBody: true,
    requiresConfirm: true,
    label: 'Book an appointment',
  },

  // ── Location (connected-location name for the UI + generated apps) ────────
  // The :locationId param is OVERWRITTEN with the caller's own location.
  { method: 'GET', pattern: '/locations/:locationId', label: 'Get location details' },
]

const SEGMENT_RE = /^[A-Za-z0-9_-]{1,64}$/

export interface AllowlistMatch {
  rule: AllowRule
  pathParams: Record<string, string>
}

/**
 * Match a client-supplied method+path against the allowlist.
 * Decodes exactly once, then rejects any residual escaping or traversal.
 * Returns null when nothing matches — callers must treat that as a 403.
 */
export function matchAllowlist(method: string, rawPath: string): AllowlistMatch | null {
  let path: string
  try {
    path = decodeURIComponent(rawPath)
  } catch {
    return null
  }
  if (path.includes('%')) return null // double-encoding (%252e…)
  if (
    !path.startsWith('/') ||
    path.includes('..') ||
    path.includes('\\') ||
    path.includes('\0') ||
    path.includes('?') ||
    path.includes('#') ||
    path.includes('//')
  ) {
    return null
  }

  // Preserve the trailing-slash distinction: '/contacts/' (list) and
  // '/contacts/:contactId' must not collide.
  const trailingSlash = path.endsWith('/')
  const pSegs = path.split('/').filter(Boolean)

  for (const rule of HL_ALLOWLIST) {
    if (rule.method !== method) continue
    const ruleTrailing = rule.pattern.endsWith('/')
    if (ruleTrailing !== trailingSlash) continue
    const rSegs = rule.pattern.split('/').filter(Boolean)
    if (rSegs.length !== pSegs.length) continue

    const pathParams: Record<string, string> = {}
    let ok = true
    for (let i = 0; i < rSegs.length; i++) {
      const r = rSegs[i]!
      const p = pSegs[i]!
      if (r.startsWith(':')) {
        if (!SEGMENT_RE.test(p)) {
          ok = false
          break
        }
        pathParams[r.slice(1)] = p
      } else if (r !== p) {
        ok = false
        break
      }
    }
    if (ok) return { rule, pathParams }
  }
  return null
}

/** Rebuild the upstream URL from OUR template — never from the client string. */
export function buildUpstreamUrl(
  match: AllowlistMatch,
  clientParams: Record<string, string | number> | undefined,
  locationId: string,
): URL {
  const path = match.rule.pattern.replace(/:([A-Za-z]+)/g, (_m, key: string) => {
    // /locations/:locationId is pinned to the caller's own location regardless
    // of what was requested.
    if (key === 'locationId') return encodeURIComponent(locationId)
    return encodeURIComponent(match.pathParams[key] ?? '')
  })
  const url = new URL(path, HL_API_BASE)
  for (const key of match.rule.allowedQuery ?? []) {
    const v = clientParams?.[key]
    if (v !== undefined && v !== null && String(v).length <= 200) {
      url.searchParams.set(key, String(v))
    }
  }
  if (match.rule.locationIdInQuery) {
    // Set LAST on a fresh URLSearchParams key so a smuggled duplicate can't survive.
    url.searchParams.set('locationId', locationId)
  }
  return url
}
