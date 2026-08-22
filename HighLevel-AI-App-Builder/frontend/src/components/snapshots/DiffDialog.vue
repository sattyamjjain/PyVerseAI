<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { collection, getDocs } from 'firebase/firestore'
import { VueMonacoDiffEditor } from '@guolao/vue-monaco-editor'
import { useMediaQuery } from '@vueuse/core'
import { FileDiff, FilePlus2, FileX2, GitCompare, Loader2 } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { db } from '@/lib/firebase'
import { languageForPath } from '@/lib/monaco'
import { computeChanges, type FileChange } from '@/lib/diff'
import { useWorkspaceStore } from '@/stores/workspace'
import { useUiStore } from '@/stores/ui'
import type { FileDoc } from '@shared/models'

const workspace = useWorkspaceStore()
const ui = useUiStore()

const loading = ref(false)
const changes = ref<FileChange[]>([])
const selected = ref<FileChange | null>(null)
const wide = useMediaQuery('(min-width: 1280px)')

const totals = computed(() => ({
  added: changes.value.reduce((s, c) => s + c.added, 0),
  removed: changes.value.reduce((s, c) => s + c.removed, 0),
}))

async function loadSnapshotFiles(snapshotId: string): Promise<Map<string, string>> {
  const projectId = workspace.projectId
  if (!projectId) return new Map()
  const snap = await getDocs(collection(db, 'projects', projectId, 'snapshots', snapshotId, 'files'))
  const map = new Map<string, string>()
  for (const d of snap.docs) {
    const data = d.data() as FileDoc
    map.set(data.path, data.content)
  }
  return map
}

watch(
  () => ui.diffDialog.open,
  async (open) => {
    if (!open) return
    loading.value = true
    changes.value = []
    selected.value = null
    try {
      const base = ui.diffDialog.base
        ? await loadSnapshotFiles(ui.diffDialog.base)
        : new Map<string, string>()
      const target =
        ui.diffDialog.target === 'current'
          ? workspace.fileContents
          : await loadSnapshotFiles(ui.diffDialog.target)
      changes.value = computeChanges(base, target)
      selected.value = changes.value[0] ?? null
    } finally {
      loading.value = false
    }
  },
)

const statusMeta = {
  A: { icon: FilePlus2, class: 'border-success/50 text-success' },
  M: { icon: FileDiff, class: 'border-info/50 text-info' },
  D: { icon: FileX2, class: 'border-destructive/50 text-destructive-soft' },
} as const

const diffOptions = computed(() => ({
  readOnly: true,
  renderSideBySide: wide.value,
  minimap: { enabled: false },
  fontSize: 12,
  lineHeight: 19,
  fontFamily: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
  scrollBeyondLastLine: false,
  automaticLayout: true,
}))
</script>

<template>
  <Dialog :open="ui.diffDialog.open" @update:open="(v) => !v && ui.closeDiff()">
    <DialogContent class="flex h-[85vh] flex-col gap-0 p-0 sm:max-w-6xl">
      <DialogHeader class="border-b border-border px-4 py-3">
        <DialogTitle class="flex items-center gap-2 text-[15px]">
          <GitCompare class="size-4" aria-hidden="true" />
          {{ ui.diffDialog.title || 'Changes' }}
          <span class="ml-2 font-mono text-xs font-normal text-muted-foreground">
            <span class="text-success">+{{ totals.added }}</span>
            <span class="text-destructive-soft"> −{{ totals.removed }}</span>
          </span>
        </DialogTitle>
        <DialogDescription class="sr-only">
          Side-by-side comparison of the files that changed between the two versions.
        </DialogDescription>
      </DialogHeader>

      <div v-if="loading" class="flex flex-1 items-center justify-center">
        <Loader2 class="size-5 animate-spin text-muted-foreground" aria-hidden="true" />
        <span class="sr-only">Loading diff</span>
      </div>
      <div v-else-if="changes.length === 0" class="flex flex-1 items-center justify-center">
        <p class="text-[13px] text-muted-foreground">No differences.</p>
      </div>
      <div v-else class="flex min-h-0 flex-1">
        <ScrollArea class="w-60 shrink-0 border-r border-border">
          <ul class="py-1" aria-label="Changed files">
            <li v-for="change in changes" :key="change.path">
              <button
                type="button"
                :aria-current="selected?.path === change.path || undefined"
                class="flex h-8 w-full items-center gap-2 px-3 text-left hover:bg-accent"
                :class="{ 'bg-secondary': selected?.path === change.path }"
                @click="selected = change"
              >
                <component
                  :is="statusMeta[change.status].icon"
                  class="size-3.5 shrink-0"
                  :class="statusMeta[change.status].class.split(' ')[1]"
                  aria-hidden="true"
                />
                <span class="min-w-0 flex-1 truncate font-mono text-xs">{{ change.path }}</span>
                <Badge variant="outline" class="px-1 text-[10px]" :class="statusMeta[change.status].class">
                  {{ change.status }}
                </Badge>
              </button>
            </li>
          </ul>
        </ScrollArea>
        <div class="min-w-0 flex-1">
          <VueMonacoDiffEditor
            v-if="selected"
            :key="selected.path"
            :original="selected.before"
            :modified="selected.after"
            :language="languageForPath(selected.path)"
            theme="genesis-dark"
            :options="diffOptions"
          />
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
