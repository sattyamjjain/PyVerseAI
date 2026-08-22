import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  addDoc,
  collection,
  doc,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  updateDoc,
  where,
} from 'firebase/firestore'
import { auth, db } from '@/lib/firebase'
import type { ProjectDoc } from '@shared/models'

export type ProjectRow = ProjectDoc & { id: string }

export const useProjectsStore = defineStore('projects', () => {
  const active = ref<ProjectRow[]>([])
  const trashed = ref<ProjectRow[]>([])
  const loading = ref(true)

  let unsubs: Array<() => void> = []

  function subscribe() {
    unsubscribe()
    const uid = auth.currentUser?.uid
    if (!uid) return
    loading.value = true
    const base = collection(db, 'projects')
    const mk = (isTrashed: boolean, target: typeof active) =>
      onSnapshot(
        query(
          base,
          where('ownerUid', '==', uid),
          where('softDeleted', '==', isTrashed),
          orderBy('updatedAt', 'desc'),
        ),
        (snap) => {
          target.value = snap.docs.map((d) => ({ id: d.id, ...(d.data() as ProjectDoc) }))
          loading.value = false
        },
        () => {
          loading.value = false
        },
      )
    unsubs = [mk(false, active), mk(true, trashed)]
  }

  function unsubscribe() {
    unsubs.forEach((u) => u())
    unsubs = []
  }

  async function createProject(name: string, description: string): Promise<string> {
    const uid = auth.currentUser?.uid
    if (!uid) throw new Error('Not signed in')
    const refDoc = await addDoc(collection(db, 'projects'), {
      ownerUid: uid,
      name: name.trim(),
      description: description.trim(),
      locationId: null,
      status: 'draft',
      softDeleted: false,
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
    })
    return refDoc.id
  }

  async function renameProject(id: string, name: string) {
    await updateDoc(doc(db, 'projects', id), { name: name.trim(), updatedAt: serverTimestamp() })
  }

  async function setTrashed(id: string, softDeleted: boolean) {
    await updateDoc(doc(db, 'projects', id), { softDeleted, updatedAt: serverTimestamp() })
  }

  return {
    active,
    trashed,
    loading,
    subscribe,
    unsubscribe,
    createProject,
    renameProject,
    setTrashed,
  }
})
