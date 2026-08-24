# End-to-end evidence

Dated artifacts from real runs, so the claims in [PRODUCTION_READINESS.md](../PRODUCTION_READINESS.md) trace to observations rather than assertions. All runs use the headless SSE harness (`scripts/gen-test.mjs`), which signs in a test user, consumes the real SSE stream, and asserts the full event sequence plus the Firestore end-state.

## Full generation (real Claude, 2026-08-24)

Command: `node scripts/gen-test.mjs gen "Build a contact dashboard with search, tag filters, and a panel of upcoming appointments"`

```text
  → app.js (create) ✓ 6150B
  snapshot Z8VjGoqgKPkfpAIT93T2 (3 files)
  done: end_turn, usage={"inputTokens":61,"outputTokens":10675,"cacheReadInputTokens":0}

stream closed after 81.4s — events: generation_start, narration_delta×6,
file_start×3, file_delta×89, file_complete×3, snapshot_created, done;
narration 508 chars
event-sequence assertions passed ✓

Firestore state — files: 3, snapshots: 1, messages: 2
  file styles.css (6300 chars)
  file app.js (6150 chars)
  file index.html (4027 chars)
  snapshot [generation] Contact Dashboard files=3
```

Points proven: SSE event protocol in the asserted order; server-side parser emitting clean per-file boundaries across 89 chunks; per-file Firestore persistence at `file_complete`; snapshot appended; chat history persisted.

## Prompt caching (real Claude, 2026-08-22 golden battery)

A refinement on an existing project reported `cache_read_input_tokens: 6386` in the generation's stored usage — the byte-frozen system prompt and stable sorted project files hit Anthropic's prefix cache, pricing cached input at 0.1×. First generations report `cacheReadInputTokens: 0` (nothing cached yet), as visible in the run above.

## Refinement contract (2026-08-22 golden battery)

A follow-up prompt ("add a phone column") re-emitted only the changed files; unchanged files kept their Firestore doc IDs and byte-identical content. The diff view showed the delta against the prior snapshot.

## Cancellation (2026-08-22 golden battery)

Stop pressed mid-stream: the in-flight partial file was discarded, files already at a `file_complete` boundary were kept, the generation doc settled to `aborted`, and the project unlocked for the next prompt.

## Rate limiting (2026-08-22, observed live)

A sixth `generate` call inside one minute returned the rate-limit error envelope (per-uid fixed window, 5/min); the SSE client surfaced it as a clear, recoverable error. Counter docs carry `expireAt` for TTL cleanup.

## Write actions with confirmation (2026-08-22, observed live)

A generated app calling `genesis.contacts.create(...)` popped the parent-rendered confirmation dialog; on Allow, `hlProxy` returned 200 and the contact appeared in the (mock-mode) CRM list. On Deny, the SDK promise rejected and the sandbox received only the rejection — no network path exists from the sandbox itself.

## Webhook fan-out (2026-08-22, emulator)

A signed webhook POST produced: signature verification pass, dedupe on `webhookId` (second delivery ignored), an `hl_events` doc, a workspace toast, and a `genesis.on('contactCreated')` event delivered into the running preview.

---

Reproduce any of these against the emulators with `HL_MOCK_MODE=true` (no HighLevel account needed): see [Local setup](../README.md#local-setup-firebase-emulators). Generation requires an `ANTHROPIC_API_KEY` in `functions/.secret.local`.
