/**
 * Deterministic HighLevel fixtures for emulator development (HL_MOCK_MODE).
 * Shapes mirror the real API responses (verified against the official
 * OpenAPI specs) so generated apps behave identically when real credentials
 * are wired in.
 */
import type { HlFetchResult } from './client.js'
import type { HlTokenResponse } from './client.js'

export const MOCK_LOCATION_ID = 'mockLoc0000000000001'

export const MOCK_TOKENS: HlTokenResponse = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  expires_in: 86_399,
  scope: 'contacts.readonly contacts.write conversations.readonly calendars.readonly',
  locationId: MOCK_LOCATION_ID,
  companyId: 'mockCompany000000001',
  userType: 'Location',
  userId: 'mockUser000000000001',
}

const now = () => Date.now()
const daysAgo = (d: number) => new Date(now() - d * 86_400_000).toISOString()
const hoursFromNow = (h: number) => new Date(now() + h * 3_600_000)

const FIRST = ['Ava', 'Liam', 'Maya', 'Noah', 'Zoe', 'Ethan', 'Ira', 'Kabir', 'Sara', 'Dev', 'Nina', 'Omar']
const LAST = ['Patel', 'Nguyen', 'Garcia', 'Smith', 'Khan', 'Rossi', 'Mehta', 'Lee', 'Brown', 'Silva', 'Iyer', 'Das']
const TAGS = [['lead'], ['customer', 'vip'], ['lead', 'webinar'], ['customer'], ['cold']]

export const MOCK_CONTACTS = FIRST.map((first, i) => ({
  id: `mockContact${String(i + 1).padStart(8, '0')}`,
  locationId: MOCK_LOCATION_ID,
  firstName: first,
  lastName: LAST[i]!,
  contactName: `${first} ${LAST[i]}`,
  email: `${first.toLowerCase()}.${LAST[i]!.toLowerCase()}@example.com`,
  phone: `+1555${String(2000000 + i * 137)}`,
  tags: TAGS[i % TAGS.length]!,
  type: i % 3 === 0 ? 'customer' : 'lead',
  source: i % 2 === 0 ? 'website form' : 'referral',
  dateAdded: daysAgo(30 - i * 2),
  dateUpdated: daysAgo(i),
  country: 'US',
  customFields: [],
}))

const MOCK_CONVERSATIONS = MOCK_CONTACTS.slice(0, 6).map((c, i) => ({
  id: `mockConvo${String(i + 1).padStart(8, '0')}`,
  contactId: c.id,
  locationId: MOCK_LOCATION_ID,
  fullName: c.contactName,
  contactName: c.contactName,
  email: c.email,
  phone: c.phone,
  type: 'TYPE_PHONE',
  unreadCount: i % 3,
  lastMessageBody: [
    'Sounds good, see you Thursday!',
    'Can you send the pricing sheet?',
    'Thanks for the quick reply 🙌',
    'Is the 3pm slot still open?',
    'Just booked through your site.',
    'Please call me back when free.',
  ][i]!,
  lastMessageType: i % 2 === 0 ? 'TYPE_SMS' : 'TYPE_EMAIL',
  lastMessageDate: new Date(now() - i * 5_400_000).toISOString(),
}))

function mockMessages(conversationId: string) {
  const convo = MOCK_CONVERSATIONS.find((c) => c.id === conversationId) ?? MOCK_CONVERSATIONS[0]!
  const mk = (i: number, direction: 'inbound' | 'outbound', body: string) => ({
    id: `${conversationId}-m${i}`,
    type: 1,
    messageType: 'SMS',
    locationId: MOCK_LOCATION_ID,
    contactId: convo.contactId,
    conversationId,
    body,
    direction,
    status: 'delivered',
    contentType: 'text/plain',
    dateAdded: new Date(now() - (6 - i) * 3_600_000).toISOString(),
    attachments: [] as string[],
  })
  return [
    mk(1, 'inbound', 'Hi! I saw your ad — do you have availability this week?'),
    mk(2, 'outbound', 'Hey! Yes we do. Thursday and Friday afternoons are open.'),
    mk(3, 'inbound', 'Thursday works. What times?'),
    mk(4, 'outbound', 'We have 2pm and 4:30pm. Want me to book one?'),
    mk(5, 'inbound', convo.lastMessageBody),
  ]
}

const MOCK_CALENDARS = [
  {
    id: 'mockCal000000000001',
    name: 'Discovery Calls',
    locationId: MOCK_LOCATION_ID,
    calendarType: 'round_robin',
    slotDuration: 30,
    isActive: true,
  },
  {
    id: 'mockCal000000000002',
    name: 'Onboarding Sessions',
    locationId: MOCK_LOCATION_ID,
    calendarType: 'event',
    slotDuration: 60,
    isActive: true,
  },
]

const APPT_TITLES = [
  'Discovery call — website revamp',
  'Onboarding: CRM setup',
  'Follow-up: proposal review',
  'Quarterly strategy check-in',
  'Demo: automation workflows',
  'Kickoff: ad campaign',
]

function mockEvents() {
  return APPT_TITLES.map((title, i) => {
    const start = hoursFromNow(4 + i * 20)
    const end = new Date(start.getTime() + (i % 2 === 0 ? 30 : 60) * 60_000)
    const contact = MOCK_CONTACTS[i * 2]!
    return {
      id: `mockEvent${String(i + 1).padStart(8, '0')}`,
      title,
      calendarId: MOCK_CALENDARS[i % 2]!.id,
      locationId: MOCK_LOCATION_ID,
      contactId: contact.id,
      appointmentStatus: i === 2 ? 'new' : 'confirmed',
      assignedUserId: 'mockUser000000000001',
      address: i % 3 === 0 ? 'https://meet.google.com/mock-demo' : 'Office — 12 Main St',
      startTime: start.toISOString(),
      endTime: end.toISOString(),
      dateAdded: daysAgo(3),
      dateUpdated: daysAgo(1),
    }
  })
}

function mockFreeSlots(startDate: number) {
  const out: Record<string, { slots: string[] }> = {}
  for (let d = 0; d < 3; d++) {
    const day = new Date(startDate + d * 86_400_000)
    const key = day.toISOString().slice(0, 10)
    out[key] = {
      slots: [10, 11, 14, 16].map((h) => {
        const s = new Date(day)
        s.setHours(h, 0, 0, 0)
        return s.toISOString()
      }),
    }
  }
  return out
}

let createdCounter = 0

/** Route a proxied request to fixtures. Paths arrive already allowlist-matched. */
export function mockHlFetch(method: string, url: URL, body?: unknown): Promise<HlFetchResult> {
  const p = url.pathname
  const q = url.searchParams
  const ok = (data: unknown): Promise<HlFetchResult> => Promise.resolve({ status: 200, data })

  if (method === 'GET' && p === '/contacts/') {
    const query = (q.get('query') ?? '').toLowerCase()
    const limit = Math.min(Number(q.get('limit') ?? 20), 100)
    const filtered = query
      ? MOCK_CONTACTS.filter((c) =>
          `${c.contactName} ${c.email} ${c.phone}`.toLowerCase().includes(query),
        )
      : MOCK_CONTACTS
    const startAfterId = q.get('startAfterId')
    const startIdx = startAfterId ? filtered.findIndex((c) => c.id === startAfterId) + 1 : 0
    const page = filtered.slice(startIdx, startIdx + limit)
    const last = page[page.length - 1]
    return ok({
      contacts: page,
      count: filtered.length,
      meta: {
        total: filtered.length,
        startAfterId: last?.id ?? null,
        startAfter: last ? Date.parse(last.dateAdded) : null,
        nextPage: startIdx + limit < filtered.length ? 2 : null,
      },
    })
  }
  if (method === 'POST' && p === '/contacts/search') {
    const b = (body ?? {}) as { pageLimit?: number }
    return ok({ contacts: MOCK_CONTACTS.slice(0, b.pageLimit ?? 20), total: MOCK_CONTACTS.length })
  }
  if (method === 'GET' && /^\/contacts\/[^/]+$/.test(p)) {
    const id = p.split('/')[2]
    const contact = MOCK_CONTACTS.find((c) => c.id === id) ?? MOCK_CONTACTS[0]!
    return ok({ contact })
  }
  if (method === 'POST' && p === '/contacts/') {
    createdCounter++
    const b = (body ?? {}) as Record<string, unknown>
    const contact = {
      id: `mockCreated${String(createdCounter).padStart(6, '0')}`,
      locationId: MOCK_LOCATION_ID,
      firstName: '',
      lastName: '',
      contactName: [b.firstName, b.lastName].filter(Boolean).join(' ') || 'New contact',
      email: '',
      phone: '',
      tags: [] as string[],
      type: 'lead',
      source: 'genesis app',
      dateAdded: new Date().toISOString(),
      dateUpdated: new Date().toISOString(),
      country: 'US',
      customFields: [],
      ...b,
    }
    // Created contacts show up in subsequent list calls (newest first),
    // matching real HighLevel behavior for demo fidelity.
    MOCK_CONTACTS.unshift(contact as (typeof MOCK_CONTACTS)[number])
    return ok({ contact })
  }
  if (method === 'PUT' && /^\/contacts\/[^/]+$/.test(p)) {
    const id = p.split('/')[2]
    const base = MOCK_CONTACTS.find((c) => c.id === id) ?? MOCK_CONTACTS[0]!
    return ok({ contact: { ...base, ...(body as Record<string, unknown>) } })
  }
  if (method === 'GET' && p === '/conversations/search') {
    return ok({ conversations: MOCK_CONVERSATIONS, total: MOCK_CONVERSATIONS.length })
  }
  if (method === 'GET' && /^\/conversations\/[^/]+\/messages$/.test(p)) {
    const conversationId = p.split('/')[2]!
    return ok({
      messages: { lastMessageId: null, nextPage: false, messages: mockMessages(conversationId) },
    })
  }
  if (method === 'GET' && /^\/conversations\/[^/]+$/.test(p)) {
    const id = p.split('/')[2]
    return ok(MOCK_CONVERSATIONS.find((c) => c.id === id) ?? MOCK_CONVERSATIONS[0]!)
  }
  if (method === 'POST' && p === '/conversations/messages') {
    return ok({
      conversationId: MOCK_CONVERSATIONS[0]!.id,
      messageId: `mockMsg${Date.now()}`,
      status: 'delivered',
      msg: 'Message queued',
    })
  }
  if (method === 'GET' && p === '/calendars/') return ok({ calendars: MOCK_CALENDARS })
  if (method === 'GET' && p === '/calendars/events') return ok({ events: mockEvents() })
  if (method === 'GET' && /^\/calendars\/events\/appointments\/[^/]+$/.test(p)) {
    const id = p.split('/').pop()
    return ok({ event: mockEvents().find((e) => e.id === id) ?? mockEvents()[0]! })
  }
  if (method === 'GET' && /^\/calendars\/[^/]+\/free-slots$/.test(p)) {
    const start = Number(q.get('startDate') ?? Date.now())
    return ok({ ...mockFreeSlots(start), traceId: 'mock-trace' })
  }
  if (method === 'POST' && p === '/calendars/events/appointments') {
    const b = (body ?? {}) as Record<string, unknown>
    return ok({
      id: `mockBooked${Date.now()}`,
      appointmentStatus: 'confirmed',
      title: b.title ?? 'Appointment',
      ...b,
    })
  }
  if (method === 'GET' && /^\/locations\/[^/]+$/.test(p)) {
    return ok({
      location: {
        id: MOCK_LOCATION_ID,
        name: 'Acme Dental — Austin (Sandbox)',
        address: '12 Main St',
        city: 'Austin',
        state: 'TX',
        country: 'US',
        timezone: 'America/Chicago',
        email: 'hello@acmedental.example',
        phone: '+15552001000',
      },
    })
  }
  return Promise.resolve({ status: 404, data: { error: 'mock route not found', path: p } })
}
