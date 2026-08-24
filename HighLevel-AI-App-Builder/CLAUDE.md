# Genesis — AI-Powered HighLevel App Builder

HighLevel senior-engineer take-home: users describe an app in chat → Claude
generates it (streamed via SSE) → live preview shows real HighLevel CRM data.

## Layout
- `frontend/` — Vue 3.5 + Vite 8 + shadcn-vue (Tailwind v4, reka-ui), Pinia, Monaco 0.56
- `functions/` — Firebase Cloud Functions v2 (nodejs22, ESM, TS strict)
- `functions/src/shared/` — wire protocol + HL allowlist, imported by the frontend via `@shared`
- Root: `firebase.json`, `firestore.rules`, `firestore.indexes.json`

## Commands
- Frontend: `npm --prefix frontend run build` (type-check + build), `npm --prefix frontend run dev`
- Functions: `npm --prefix functions run build`, `npm --prefix functions test` (vitest; rules tests need the Firestore emulator)
- Emulators: `firebase emulators:start --only auth,functions,firestore --project demo-genesis`
  (demo- project = fully offline; `functions/.env` has `HL_MOCK_MODE=true`,
  secrets come from `functions/.secret.local`)

## Non-negotiable invariants
- SSE streams from `generate` are consumed at the function's DIRECT URL — never through Hosting rewrites (they buffer + 60s cap).
- HighLevel tokens live ONLY in `hl_connections/{uid}` (rules deny-all; Admin SDK only). Client-visible status is mirrored to `users/{uid}.hl` by functions.
- HL refresh tokens ROTATE: refresh only via the lease pattern in `functions/src/hl/client.ts`.
- Generated code runs in `sandbox="allow-scripts allow-forms"` srcdoc iframes with CSP `connect-src 'none'` (allow-forms only revives form events; submission stays double-blocked by `form-action 'none'` + a capture-phase preventDefault in the bootstrap); ALL data flows through the postMessage parent bridge → `hlProxy` → allowlist (`functions/src/shared/allowlist.ts` is the single source of truth).
- Firestore file writes happen at file_complete boundaries only, never per token.
- The system prompt (`functions/src/genesis/prompt.ts`) is byte-frozen for Anthropic prefix caching — never interpolate volatile values into it; project state goes into `messages` sorted-by-path.
- Claude 5 family: never send temperature/top_p/top_k or assistant prefill (400 errors).
- TypeScript is pinned `~6.0` — typescript@7 breaks vue-tsc.
- Accessibility: the a11y checklist from the design review is build-gating; the ONLY aria-live/role=status/alert regions live in `frontend/src/components/AppAnnouncer.vue`.

## Verification before claiming done
`npm --prefix functions test` · `npm --prefix frontend run build` · emulator smoke: `scratchpad/smoke.sh` pattern (auth → mock OAuth → proxy → seed).
