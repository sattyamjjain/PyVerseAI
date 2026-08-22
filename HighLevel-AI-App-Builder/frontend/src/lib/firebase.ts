import { initializeApp } from 'firebase/app'
import { connectAuthEmulator, getAuth } from 'firebase/auth'
import {
  connectFirestoreEmulator,
  initializeFirestore,
  persistentLocalCache,
  persistentMultipleTabManager,
} from 'firebase/firestore'

// The Firebase web config is public by design — it identifies the project and
// grants nothing. Security lives in Firestore rules, Auth, and the functions.
const useEmulators = import.meta.env.VITE_USE_EMULATORS
  ? import.meta.env.VITE_USE_EMULATORS === 'true'
  : import.meta.env.DEV

const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID ?? 'demo-genesis'

export const firebaseApp = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? 'demo-api-key',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? `${projectId}.firebaseapp.com`,
  projectId,
  appId: import.meta.env.VITE_FIREBASE_APP_ID ?? 'demo-app-id',
})

export const auth = getAuth(firebaseApp)
export const db = initializeFirestore(firebaseApp, {
  localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
})

if (useEmulators) {
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true })
  connectFirestoreEmulator(db, '127.0.0.1', 8080)
}

/**
 * Cloud Functions are called at their DIRECT URL — Firebase Hosting rewrites
 * buffer responses and cap requests at 60s, which kills SSE streaming.
 */
export const FUNCTIONS_BASE =
  import.meta.env.VITE_FUNCTIONS_BASE ??
  (useEmulators
    ? `http://127.0.0.1:5001/${projectId}/us-central1`
    : `https://us-central1-${projectId}.cloudfunctions.net`)

/** Fresh ID token for authenticated function calls (SDK caches + refreshes). */
export async function idToken(): Promise<string> {
  const user = auth.currentUser
  if (!user) throw new Error('Not signed in')
  return user.getIdToken()
}
