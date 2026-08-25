# Loom walkthrough — shot list (target 4:50, hard cap 5:00)

## Prep (do all of this BEFORE hitting record)

1. Fresh browser window at 1440px wide; close every other tab and app; Mac Do Not Disturb ON.
2. Brave Shields OFF for genesis-hl-builder-sj.web.app AND the HighLevel tab (Shields block Firestore's live channel).
3. Sandbox seeded: contacts, conversations, AND appointments (Seed result shows appointments > 0).
4. Second tab: HighLevel Jhansi sandbox → Contacts, ready to add a contact (for the webhook beat).
5. DRY RUN the OAuth connect once with a throwaway account before recording. If it misbehaves, record with the already-connected account and show the connected badge instead.
6. Model picker on Fast (Sonnet) — fastest stream for the money shot.

## Timeline

| ⏱ | Beat | Say (roughly) |
|---|------|----------------|
| 0:00 | Cold open on the deployed sign-up page | "This is Genesis, an AI app builder that generates working HighLevel marketplace apps. Everything here is deployed on Firebase: Hosting, Firestore, Cloud Functions. Let me sign up." |
| 0:15 | Sign up → dashboard → **Connect HighLevel** → OAuth → pick the sandbox location → connected badge | "This is the real OAuth flow: HighLevel's authorize page, a Cloud Function handles the callback, and the tokens live server-side in a Firestore collection the browser is denied from ever reading. Connected to my sandbox." |
| 0:45 | New project → name it → workspace opens → click the "Contact dashboard with search" chip → Send | "Each project is chat, editor, live preview. I'll ask for a contact dashboard with search and upcoming appointments." |
| 1:00 | THE MONEY SHOT — generation streams ~90s. Deliver the ARCHITECTURE BEAT over it, unhurried | "While this streams, the architecture I'm proudest of: the Cloud Function parses Claude's raw stream server-side with a holdback-buffer state machine and emits semantic SSE events: file-start, file-delta, file-complete. The editor is just following those events. Every file is persisted to Firestore the moment it completes, so a dropped connection loses nothing. And the app it's building will run in a sandboxed iframe with zero network access. Its only data path is a postMessage bridge into my authenticated proxy, which enforces a server-side endpoint allowlist and pins every call to my location. A prompt-injected generation physically cannot exfiltrate anything." |
| 2:30 | Done → preview shows REAL data: type in search, hover contacts, show the appointments panel | "That's my real sandbox CRM: contacts and appointments straight from the HighLevel API, live in the generated app." |
| 3:00 | Refinement: send **"Add a phone column to the contact list"** → only changed files restream → **View changes** → diff | "Refinements send the full project as context and rewrite only the files that change. And here's the Monaco diff of exactly what the model touched." |
| 3:50 | Manual edit in Monaco (change the h1 text or a color) → ⌘S → preview refreshes | "I can hand-edit anything; saves go to Firestore and the preview picks them up." |
| 4:05 | Snapshot history → Restore the first snapshot → confirm → preview reverts → Undo toast | "Every generation is a restorable snapshot, v0-style: restore backs up the current state first, history is never destroyed, so Undo is always safe." |
| 4:35 | (If webhook verified in dry run) HL tab → add a contact → toast pops in Genesis | "HighLevel webhooks push CRM changes into the running preview live, with signature verification." |
| 4:50 | Close, on the workspace | "Eighty-three tests across backend and frontend, CI on every push, Lighthouse hundreds on accessibility, best practices, and SEO. Repo and full production-readiness review are linked below. Thanks!" |

Cut-if-over-time order: webhook beat → manual-edit beat → shorten the refinement wait (talk over it and cut to the diff).
Do NOT cut: OAuth, the generation stream, real data in the preview, snapshot restore, the architecture explanation — all are explicit grading criteria.

When publishing: put the live URL, the repo deep link, and the test/Lighthouse numbers in the Loom description.
