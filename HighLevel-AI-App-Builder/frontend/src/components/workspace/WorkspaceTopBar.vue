<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { ArrowLeft, History, PanelLeftClose, PanelRightClose, Pencil, WifiOff } from 'lucide-vue-next'
import { useNetwork } from '@vueuse/core'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import GenerationStatusPill from '@/components/workspace/GenerationStatusPill.vue'
import UserMenu from '@/components/workspace/UserMenu.vue'
import HlBadge from '@/components/hl/HlBadge.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { useUiStore } from '@/stores/ui'
import { ariaMod, modKeyLabel } from '@/composables/useShortcuts'
import { announce, announceAlert } from '@/composables/useAnnouncer'

const workspace = useWorkspaceStore()
const ui = useUiStore()
const { isOnline } = useNetwork()

// Offline is announced, not just shown (WCAG 4.1.3).
watch(isOnline, (online) => {
  if (online) announce('Back online')
  else announceAlert('Connection lost — working offline')
})

const renaming = ref(false)
const renameDraft = ref('')
const renameInput = ref<HTMLInputElement | null>(null)
const renameButton = ref<HTMLButtonElement | null>(null)

async function startRename() {
  renameDraft.value = workspace.project?.name ?? ''
  renaming.value = true
  await nextTick()
  renameInput.value?.focus()
  renameInput.value?.select()
}

/** Focus-eviction: the input unmounts on commit/cancel — return to the button. */
async function endRename() {
  renaming.value = false
  await nextTick()
  renameButton.value?.focus()
}

async function commitRename() {
  if (!renaming.value) return // blur after Enter already committed
  const name = renameDraft.value.trim()
  await endRename()
  if (name && name !== workspace.project?.name) {
    await workspace.renameProject(name)
  }
}
</script>

<template>
  <header
    data-panel-cycle="topbar"
    class="flex h-12 shrink-0 items-center gap-2 border-b border-border bg-background px-2"
    tabindex="-1"
    aria-label="Workspace toolbar"
  >
    <Tooltip>
      <TooltipTrigger as-child>
        <RouterLink
          to="/projects"
          class="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Back to projects"
        >
          <ArrowLeft class="size-4" aria-hidden="true" />
        </RouterLink>
      </TooltipTrigger>
      <TooltipContent>Back to projects</TooltipContent>
    </Tooltip>
    <Separator orientation="vertical" class="h-5!" />

    <div class="flex min-w-0 items-center gap-1">
      <input
        v-if="renaming"
        ref="renameInput"
        v-model="renameDraft"
        class="h-7 w-48 rounded-md border border-border bg-card px-2 text-[13px] outline-none focus-visible:border-primary"
        aria-label="Project name"
        @keydown.enter.prevent="commitRename"
        @keydown.esc="endRename"
        @blur="commitRename"
      />
      <button
        v-else
        ref="renameButton"
        type="button"
        class="group flex min-w-0 items-center gap-1.5 rounded-md px-2 py-1 text-[13px] font-medium hover:bg-accent"
        :aria-label="`Rename project ${workspace.project?.name ?? ''}`"
        @click="startRename"
      >
        <span class="truncate">{{ workspace.project?.name ?? '…' }}</span>
        <Pencil
          class="size-3 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
          aria-hidden="true"
        />
      </button>
    </div>

    <div class="flex flex-1 justify-center">
      <Badge
        v-if="!isOnline"
        variant="outline"
        class="gap-1.5 border-warning/50 text-warning"
      >
        <WifiOff class="size-3" aria-hidden="true" /> Offline — reconnecting…
      </Badge>
      <GenerationStatusPill v-else />
    </div>

    <HlBadge />

    <Tooltip>
      <TooltipTrigger as-child>
        <button
          id="snapshot-history-btn"
          type="button"
          class="relative flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          :aria-label="`Snapshot history, ${workspace.snapshots.length} snapshots`"
          @click="ui.snapshotSheetOpen = true"
        >
          <History class="size-4" aria-hidden="true" />
          <span
            v-if="workspace.snapshots.length"
            class="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-secondary px-1 text-[9px] font-medium"
            aria-hidden="true"
          >
            {{ workspace.snapshots.length > 99 ? '99+' : workspace.snapshots.length }}
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent>Snapshot history</TooltipContent>
    </Tooltip>

    <Tooltip>
      <TooltipTrigger as-child>
        <button
          type="button"
          class="hidden size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground lg:flex"
          :class="{ 'bg-secondary text-foreground': ui.chatCollapsed }"
          :aria-label="ui.chatCollapsed ? 'Show chat panel' : 'Hide chat panel'"
          :aria-expanded="!ui.chatCollapsed"
          :aria-keyshortcuts="`${ariaMod}+B`"
          @click="ui.chatCollapsed = !ui.chatCollapsed"
        >
          <PanelLeftClose class="size-4" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent>{{ ui.chatCollapsed ? 'Show' : 'Hide' }} chat ({{ modKeyLabel }}B)</TooltipContent>
    </Tooltip>

    <Tooltip>
      <TooltipTrigger as-child>
        <button
          type="button"
          class="hidden size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground lg:flex"
          :class="{ 'bg-secondary text-foreground': ui.previewCollapsed }"
          :aria-label="ui.previewCollapsed ? 'Show preview panel' : 'Hide preview panel'"
          :aria-expanded="!ui.previewCollapsed"
          @click="ui.previewCollapsed = !ui.previewCollapsed"
        >
          <PanelRightClose class="size-4" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent>{{ ui.previewCollapsed ? 'Show' : 'Hide' }} preview</TooltipContent>
    </Tooltip>

    <UserMenu show-shortcuts />
  </header>
</template>
