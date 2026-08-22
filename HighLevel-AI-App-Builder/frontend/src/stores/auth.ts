import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User,
} from 'firebase/auth'
import { doc, onSnapshot, serverTimestamp, setDoc } from 'firebase/firestore'
import { auth, db } from '@/lib/firebase'
import type { UserDoc } from '@shared/models'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const profile = ref<UserDoc | null>(null)
  const ready = ref(false)

  let unsubProfile: (() => void) | null = null

  onAuthStateChanged(auth, (u) => {
    user.value = u
    ready.value = true
    unsubProfile?.()
    unsubProfile = null
    profile.value = null
    if (u) {
      unsubProfile = onSnapshot(doc(db, 'users', u.uid), (snap) => {
        profile.value = (snap.data() as UserDoc | undefined) ?? null
      })
    }
  })

  const hl = computed(() => profile.value?.hl ?? null)
  const hlConnected = computed(() => hl.value?.status === 'connected')

  async function signUp(email: string, password: string, displayName: string) {
    const cred = await createUserWithEmailAndPassword(auth, email, password)
    // Keys must match the users create rule exactly.
    await setDoc(doc(db, 'users', cred.user.uid), {
      displayName,
      email,
      createdAt: serverTimestamp(),
    })
  }

  async function signIn(email: string, password: string) {
    await signInWithEmailAndPassword(auth, email, password)
  }

  async function signOutUser() {
    await signOut(auth)
  }

  return { user, profile, ready, hl, hlConnected, signUp, signIn, signOutUser }
})
