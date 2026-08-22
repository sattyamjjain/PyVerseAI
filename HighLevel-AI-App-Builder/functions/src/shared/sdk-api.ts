/**
 * The `genesis` SDK surface injected into preview iframes — the contract
 * between (a) the preview bootstrap implementation in the SPA, and (b) the
 * system prompt that documents it to the LLM. Every method maps mechanically
 * onto one allowlisted HighLevel route (see allowlist.ts); the bridge carries
 * {method, path, params, body} and the parent/proxy enforce everything.
 *
 * Keep this table and the prompt's <genesis_sdk> section in lockstep.
 */

export interface SdkMethodSpec {
  /** Dotted SDK name, e.g. "contacts.list". */
  name: string
  method: 'GET' | 'POST' | 'PUT'
  /** Path template with :params filled from the args object. */
  path: string
  /** True when the parent shows a confirmation dialog before forwarding. */
  requiresConfirm: boolean
  /** Signature documentation used in the system prompt. */
  doc: string
}

export const GENESIS_SDK_METHODS: readonly SdkMethodSpec[] = [
  {
    name: 'contacts.list',
    method: 'GET',
    path: '/contacts/',
    requiresConfirm: false,
    doc: 'genesis.contacts.list({ limit?, startAfter?, startAfterId?, query? }) → { contacts: Contact[], count, meta: { startAfter, startAfterId, nextPage } }. limit ≤ 100. Paginate by passing BOTH meta.startAfter and meta.startAfterId from the previous page.',
  },
  {
    name: 'contacts.search',
    method: 'POST',
    path: '/contacts/search',
    requiresConfirm: false,
    doc: 'genesis.contacts.search({ filters?, sort?, page?, pageLimit? }) → { contacts: Contact[], total }. filters: [{ field, operator ("eq"|"contains"|"exists"), value }].',
  },
  {
    name: 'contacts.get',
    method: 'GET',
    path: '/contacts/:contactId',
    requiresConfirm: false,
    doc: 'genesis.contacts.get(contactId) → { contact: Contact }',
  },
  {
    name: 'contacts.create',
    method: 'POST',
    path: '/contacts/',
    requiresConfirm: true,
    doc: 'genesis.contacts.create({ firstName?, lastName?, email?, phone?, tags?, ... }) → { contact: Contact }. Asks the user for confirmation before running.',
  },
  {
    name: 'contacts.update',
    method: 'PUT',
    path: '/contacts/:contactId',
    requiresConfirm: true,
    doc: 'genesis.contacts.update(contactId, { firstName?, email?, tags?, ... }) → { contact: Contact }. Asks the user for confirmation before running.',
  },
  {
    name: 'conversations.list',
    method: 'GET',
    path: '/conversations/search',
    requiresConfirm: false,
    doc: 'genesis.conversations.list({ limit?, status? ("all"|"read"|"unread"|"starred"), sortBy?, sort?, contactId?, query?, startAfterDate? }) → { conversations: Conversation[], total }. Paginate with startAfterDate = last item sort value (epoch ms).',
  },
  {
    name: 'conversations.get',
    method: 'GET',
    path: '/conversations/:conversationId',
    requiresConfirm: false,
    doc: 'genesis.conversations.get(conversationId) → conversation details',
  },
  {
    name: 'conversations.messages',
    method: 'GET',
    path: '/conversations/:conversationId/messages',
    requiresConfirm: false,
    doc: 'genesis.conversations.messages(conversationId, { limit?, lastMessageId?, type? }) → { messages: Message[], lastMessageId, nextPage }. Paginate with lastMessageId while nextPage is true.',
  },
  {
    name: 'conversations.send',
    method: 'POST',
    path: '/conversations/messages',
    requiresConfirm: true,
    doc: 'genesis.conversations.send({ type: "SMS"|"Email", contactId, message?, html?, subject? }) → { conversationId, messageId, status }. Asks the user for confirmation before sending.',
  },
  {
    name: 'calendars.list',
    method: 'GET',
    path: '/calendars/',
    requiresConfirm: false,
    doc: 'genesis.calendars.list({ groupId? }) → { calendars: Calendar[] }',
  },
  {
    name: 'calendars.events',
    method: 'GET',
    path: '/calendars/events',
    requiresConfirm: false,
    doc: 'genesis.calendars.events({ startTime, endTime, calendarId? | userId? | groupId? }) → { events: Appointment[] }. startTime/endTime are epoch MILLISECONDS; exactly one of calendarId/userId/groupId is required; event times in responses are ISO strings.',
  },
  {
    name: 'calendars.appointment',
    method: 'GET',
    path: '/calendars/events/appointments/:eventId',
    requiresConfirm: false,
    doc: 'genesis.calendars.appointment(eventId) → { event: Appointment }',
  },
  {
    name: 'calendars.freeSlots',
    method: 'GET',
    path: '/calendars/:calendarId/free-slots',
    requiresConfirm: false,
    doc: 'genesis.calendars.freeSlots(calendarId, { startDate, endDate, timezone? }) → { "<YYYY-MM-DD>": { slots: string[] }, ... }. startDate/endDate epoch MILLISECONDS, range ≤ 31 days; iterate date keys, skip non-date keys.',
  },
  {
    name: 'calendars.book',
    method: 'POST',
    path: '/calendars/events/appointments',
    requiresConfirm: true,
    doc: 'genesis.calendars.book({ calendarId, contactId, startTime, endTime?, title?, appointmentStatus? }) → Appointment. startTime is an ISO-8601 string WITH timezone offset. Asks the user for confirmation before booking.',
  },
  {
    name: 'location.get',
    method: 'GET',
    path: '/locations/me',
    requiresConfirm: false,
    doc: "genesis.location.get() → { location: { id, name, timezone, email, phone, ... } } — the connected location's details.",
  },
]

/**
 * Events the parent may broadcast into the preview when HighLevel webhooks
 * arrive. Subscribed via genesis.on(event, callback).
 */
export const GENESIS_SDK_EVENTS = [
  'contactCreated',
  'contactUpdated',
  'contactDeleted',
  'inboundMessage',
  'appointmentCreated',
  'appointmentUpdated',
] as const
export type GenesisSdkEvent = (typeof GENESIS_SDK_EVENTS)[number]
