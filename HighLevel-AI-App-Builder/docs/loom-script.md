# Loom walkthrough — shot list (target 4:30, hard cap 5:00)

Prep before recording: deployed app open in a fresh incognito window · HighLevel
sandbox already seeded (Connect dialog → Seed demo data) · one calendar exists in
the sandbox · second tab logged into the HighLevel sandbox (for the webhook beat)
· close everything else; 1440px-wide window; mic check.

| ⏱ | Beat | Say (roughly) |
|---|------|----------------|
| 0:00 | Cold open on the deployed sign-up page | "This is Genesis — an AI app builder that generates working HighLevel marketplace apps. Everything you'll see is deployed on Firebase: Hosting, Firestore, and Cloud Functions. Let me sign up." |
| 0:20 | Sign up → dashboard → click **Connect HighLevel** → OAuth popup → pick sandbox location → dialog flips to connected | "Connecting my HighLevel account — this is the real OAuth flow: the popup goes to HighLevel's authorize page, a Cloud Function handles the callback, and tokens are stored server-side where the browser can never read them. There's my sandbox location." |
| 0:50 | New project → "Contact Dashboard" → workspace opens | "Each project is a chat, a code editor, and a live preview." |
| 1:00 | Click the suggestion chip, tweak to: **"Build a contact dashboard with search and a list of upcoming appointments"** → Send | "I'll ask for a contact dashboard with search plus upcoming appointments." |
| 1:10 | THE MONEY SHOT — let it run ~45s with light narration | "The Cloud Function streams Claude over server-sent events. Watch the plan stream into chat… now each file — the editor follows the stream as code types in live, and every file is persisted to Firestore the moment it completes, so nothing is lost if the connection drops. File chips show per-file progress." |
| 1:55 | Generation completes → preview refreshes with REAL data; hover a contact, use the search box, scroll to appointments | "And that's my real sandbox CRM data — these contacts and appointments come from the HighLevel API. The generated app runs in a locked-down iframe with zero network access; its only data path is a postMessage bridge to my authenticated proxy, which enforces an endpoint allowlist and pins every call to my location." |
| 2:30 | Refinement: send **"Make the table rows denser and add a tag filter dropdown"** → point out only changed files re-stream → click **View changes** → diff dialog | "Refinements send the full project as context and rewrite only the files that change — and here's the diff for exactly what the model touched." |
| 3:10 | Edit a file manually in Monaco (change a color/title) → ⌘S → preview refresh | "I can hand-edit anything — saves go straight to Firestore and the preview picks them up." |
| 3:30 | Snapshot history sheet → restore the first snapshot → confirm dialog ("backup created first") → preview reverts → undo toast | "Every generation is a restorable snapshot. Restore is append-only, v0-style: it backs up the current state first, so history is never destroyed — that's why Undo is safe." |
| 4:00 | ARCHITECTURE BEAT (talking head or stay on screen) | "The decision I'm proudest of: the LLM stream is parsed **server-side** with a holdback-buffer state machine that turns raw tokens into semantic SSE events — file-start, file-delta, file-complete. The browser stays dumb, Firestore is the single durable source of truth, and one parser serves streaming UX, persistence, validation, and repair. It also means a prompt-injected generation physically can't exfiltrate anything: the sandbox has no network, and the only bridge enforces the same server-side allowlist." |
| 4:30 | (If time) create a contact in the HL sandbox tab → toast pops in Genesis ("New contact…") → click Refresh preview | "Bonus: HighLevel webhooks push CRM changes into the running preview live." |
| 4:50 | Close | "Genesis — repo and README linked below. Thanks!" |

Cut-if-over-time order: webhook beat → manual-edit beat → shorten the money-shot narration.
Do NOT cut: OAuth, generation stream, real data in preview, snapshot restore, the architecture beat (all are explicit grading criteria).
