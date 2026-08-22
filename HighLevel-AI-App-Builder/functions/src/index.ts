/**
 * Genesis Cloud Functions.
 *
 * Every browser-facing endpoint is an onRequest called at its DIRECT URL
 * (https://us-central1-<project>.cloudfunctions.net/<name>) — Firebase
 * Hosting rewrites buffer responses and cap requests at 60s, which would
 * break the SSE generation stream, so nothing routes through Hosting.
 */
export { generate } from './generate.js'
export { hlProxy } from './proxy.js'
export { hlAuthStart, hlAuthCallback, hlDisconnect } from './oauth.js'
export { hlWebhook } from './webhook.js'
export { restoreSnapshot } from './snapshots.js'
export { seedSandbox } from './seed.js'
