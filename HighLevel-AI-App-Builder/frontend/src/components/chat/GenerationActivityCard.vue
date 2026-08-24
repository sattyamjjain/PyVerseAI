<script setup lang="ts">
import { computed, nextTick } from 'vue'
import {
  Check,
  ChevronDown,
  CircleAlert,
  CircleSlash,
  FileCode2,
  FilePlus2,
  GitCompare,
  Loader2,
  RotateCcw,
  TriangleAlert,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { formatDuration } from '@/lib/time'
import { useGenerationStore } from '@/stores/generation'
import { useWorkspaceStore } from '@/stores/workspace'
import { useUiStore } from '@/stores/ui'
import type { MessageDoc } from '@shared/models'

/**
 * The per-generation activity card (bolt-style). Two modes:
 *  - live: driven by the generation store during/after a stream
 *  - persisted: rendered from a stored assistant message's meta
 */
const props = defineProps<{
  mode: 'live' | 'persisted'
  meta?: MessageDoc['meta']
}>()

const emit = defineEmits<{ continueGen: []; dismiss: [] }>()

const generation = useGenerationStore()
const workspace = useWorkspaceStore()
const ui = useUiStore()

const live = computed(() => props.mode === 'live')
const working = computed(
  () => live.value && ['sending', 'planning', 'streaming', 'finalizing', 'stopping'].includes(generation.phase),
)

const totals = computed(() => {
  if (!live.value) {
    return {
      files: props.meta?.filesChanged.length ?? 0,
      added: props.meta?.added ?? 0,
      removed: props.meta?.removed ?? 0,
      duration: props.meta?.durationMs ?? 0,
    }
  }
  return {
    files: generation.liveFiles.length,
    added: generation.liveFiles.reduce((s, f) => s + f.added, 0),
    removed: generation.liveFiles.reduce((s, f) => s + f.removed, 0),
    duration: generation.durationMs,
  }
})

const headerText = computed(() => {
  if (live.value) {
    if (working.value) return 'Working…'
    if (generation.phase === 'failed') return 'Generation failed'
    if (generation.phase === 'stopped') return 'Stopped'
    return `Generated ${totals.value.files} ${totals.value.files === 1 ? 'file' : 'files'} in ${formatDuration(totals.value.duration)}`
  }
  return `Generated ${totals.value.files} ${totals.value.files === 1 ? 'file' : 'files'} in ${formatDuration(totals.value.duration)}`
})

function onRetry() {
  generation.retry()
  // The error footer (and this Retry button) unmounts — keep focus in chat.
  void nextTick(() => document.querySelector<HTMLElement>('#prompt-input')?.focus())
}

function openDiffForThis() {
  const snapshotId = live.value ? generation.lastSnapshotId : props.meta?.snapshotId
  if (!snapshotId) return
  const idx = workspace.snapshots.findIndex((s) => s.id === snapshotId)
  const base = idx >= 0 ? (workspace.snapshots[idx + 1]?.id ?? null) : null
  ui.openDiff(base, snapshotId, 'Changes in this generation')
}

const persistedFiles = computed(() => props.meta?.filesChanged ?? [])
const showSummaryFooter = computed(() =>
  live.value ? generation.phase === 'done' : (props.meta?.snapshotId ?? null) !== null,
)
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-border/70 bg-card">
    <!-- Header -->
    <div class="flex items-center gap-2 border-b border-border px-3 py-2">
      <Loader2 v-if="working" class="size-4 animate-spin text-primary" aria-hidden="true" />
      <CircleAlert
        v-else-if="live && generation.phase === 'failed'"
        class="size-4 text-destructive-soft"
        aria-hidden="true"
      />
      <CircleSlash
        v-else-if="live && generation.phase === 'stopped'"
        class="size-4 text-muted-foreground"
        aria-hidden="true"
      />
      <Check v-else class="size-4 text-success" aria-hidden="true" />
      <span class="flex-1 text-[13px] font-medium">{{ headerText }}</span>
      <span
        v-if="totals.added + totals.removed > 0"
        class="font-mono text-[11px] text-muted-foreground"
      >
        <span class="text-success">+{{ totals.added }}</span>
        <span class="text-destructive-soft"> −{{ totals.removed }}</span>
      </span>
    </div>

    <!-- Live file chips -->
    <ul v-if="live && generation.liveFiles.length" class="py-1">
      <li v-for="file in generation.liveFiles" :key="file.path">
        <button
          type="button"
          class="flex h-[30px] w-full items-center gap-2 px-3 text-left transition-colors duration-150 hover:bg-accent"
          :aria-label="`Open ${file.path}, ${file.status === 'done' ? 'completed' : 'writing'}${file.truncated ? ', truncated' : ''}`"
          @click="workspace.openFile(file.path)"
        >
          <FilePlus2
            v-if="file.action === 'create'"
            class="size-3.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <FileCode2 v-else class="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span class="min-w-0 flex-1 truncate font-mono text-xs">{{ file.path }}</span>
          <span
            v-if="file.status === 'done' && file.added + file.removed > 0"
            class="font-mono text-[11px] text-muted-foreground"
          >
            <span class="text-success">+{{ file.added }}</span>
            <span class="text-destructive-soft"> −{{ file.removed }}</span>
          </span>
          <TriangleAlert
            v-if="file.truncated"
            class="size-3.5 shrink-0 text-warning"
            aria-hidden="true"
          />
          <Loader2
            v-if="file.status === 'writing'"
            class="size-3.5 shrink-0 animate-spin text-primary"
            aria-hidden="true"
          />
          <Check v-else class="size-3.5 shrink-0 text-success" aria-hidden="true" />
        </button>
      </li>
    </ul>

    <!-- Persisted file list -->
    <ul v-else-if="!live && persistedFiles.length" class="py-1">
      <li v-for="path in persistedFiles" :key="path">
        <button
          type="button"
          class="flex h-[30px] w-full items-center gap-2 px-3 text-left transition-colors duration-150 hover:bg-accent"
          :aria-label="`Open ${path}`"
          @click="workspace.openFile(path)"
        >
          <FileCode2 class="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          <span class="min-w-0 flex-1 truncate font-mono text-xs">{{ path }}</span>
        </button>
      </li>
    </ul>

    <!-- Error footer -->
    <div v-if="live && generation.phase === 'failed' && generation.error" class="border-t border-destructive/30 bg-destructive/10 px-3 py-2">
      <p class="text-[13px] text-destructive-soft">{{ generation.error.message }}</p>
      <Collapsible v-if="generation.error.code" class="mt-1">
        <CollapsibleTrigger
          class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ChevronDown class="size-3" aria-hidden="true" /> Show details
        </CollapsibleTrigger>
        <CollapsibleContent>
          <p class="mt-1 font-mono text-xs text-muted-foreground">code: {{ generation.error.code }}</p>
        </CollapsibleContent>
      </Collapsible>
      <div class="mt-2 flex gap-2">
        <Button
          v-if="generation.error.recoverable"
          size="sm"
          variant="secondary"
          @click="onRetry"
        >
          <RotateCcw class="size-3.5" aria-hidden="true" /> Retry
        </Button>
        <Button size="sm" variant="ghost" @click="emit('dismiss')">Dismiss</Button>
      </div>
    </div>

    <!-- Stopped footer -->
    <div v-else-if="live && generation.phase === 'stopped'" class="border-t border-border px-3 py-2">
      <p class="text-[13px] text-muted-foreground">
        Stopped. Kept {{ generation.liveFiles.filter((f) => f.status === 'done').length }} completed
        {{ generation.liveFiles.filter((f) => f.status === 'done').length === 1 ? 'file' : 'files' }}.
      </p>
      <div class="mt-2 flex gap-2">
        <Button size="sm" variant="secondary" @click="emit('continueGen')">Continue</Button>
        <Button size="sm" variant="ghost" @click="emit('dismiss')">Dismiss</Button>
      </div>
    </div>

    <!-- Success footer -->
    <div v-else-if="showSummaryFooter" class="flex items-center justify-between border-t border-border px-3 py-1.5">
      <span class="text-xs text-muted-foreground">Snapshot saved</span>
      <Button size="sm" variant="ghost" class="h-7 text-xs" @click="openDiffForThis">
        <GitCompare class="size-3.5" aria-hidden="true" /> View changes
      </Button>
    </div>
  </div>
</template>
