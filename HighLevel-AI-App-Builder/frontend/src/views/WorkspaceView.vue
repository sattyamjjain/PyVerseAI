<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArchiveRestore, FileQuestion, Loader2, Trash2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import WorkspaceTopBar from '@/components/workspace/WorkspaceTopBar.vue'
import CommandPalette from '@/components/workspace/CommandPalette.vue'
import ShortcutsDialog from '@/components/workspace/ShortcutsDialog.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import EditorPanel from '@/components/editor/EditorPanel.vue'
import PreviewPanel from '@/components/preview/PreviewPanel.vue'
import SnapshotSheet from '@/components/snapshots/SnapshotSheet.vue'
import DiffDialog from '@/components/snapshots/DiffDialog.vue'
import ConfirmActionDialog from '@/components/preview/ConfirmActionDialog.vue'
import HlConnectDialog from '@/components/hl/HlConnectDialog.vue'
import { useShortcuts } from '@/composables/useShortcuts'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { usePreviewStore } from '@/stores/preview'
import { useUiStore } from '@/stores/ui'
import '@/lib/monaco'

const route = useRoute()
const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const preview = usePreviewStore()
const ui = useUiStore()

const chatRef = ref<InstanceType<typeof ChatPanel> | null>(null)

watch(
  () => route.params.id,
  (id) => {
    if (typeof id === 'string' && route.name === 'workspace') workspace.open(id)
  },
  { immediate: true },
)
onBeforeUnmount(() => workspace.close())

watch(
  () => workspace.project?.name,
  (name) => {
    if (name) document.title = `${name} - Genesis`
  },
)

const state = computed<'loading' | 'missing' | 'trashed' | 'ready'>(() => {
  if (workspace.projectLoading) return 'loading'
  if (workspace.projectMissing) return 'missing'
  if (workspace.project?.softDeleted) return 'trashed'
  return 'ready'
})

// ── keyboard ────────────────────────────────────────────────────────────────
function cyclePanels(dir: 1 | -1) {
  const targets = [...document.querySelectorAll<HTMLElement>('[data-panel-cycle]')].filter(
    // offsetWidth check: a collapsed splitter panel keeps an offsetParent.
    (el) => el.offsetParent !== null && el.offsetWidth > 0,
  )
  if (targets.length === 0) return
  const current = targets.findIndex((el) => el.contains(document.activeElement))
  const next = targets[(current + dir + targets.length) % targets.length]
  next?.focus()
}

useShortcuts([
  { key: 'k', mod: true, allowInInput: true, handler: () => (ui.paletteOpen = !ui.paletteOpen) },
  {
    key: 's',
    mod: true,
    allowInInput: true,
    handler: () => {
      if (workspace.activePath) {
        void workspace.saveFile(workspace.activePath, { announceResult: true })
      }
    },
  },
  {
    key: 'b',
    mod: true,
    allowInInput: true,
    handler: () => {
      const collapsing = !ui.chatCollapsed
      const chatEl = document.querySelector('[data-panel-cycle="chat"]')
      ui.chatCollapsed = collapsing
      // Focus-eviction: collapsing the panel that holds focus lands on topbar.
      if (collapsing && chatEl?.contains(document.activeElement)) {
        document.querySelector<HTMLElement>('[data-panel-cycle="topbar"]')?.focus()
      }
    },
  },
  { key: 'j', mod: true, allowInInput: true, handler: () => (preview.consoleOpen = !preview.consoleOpen) },
  { key: '.', mod: true, allowInInput: true, handler: () => generation.cancel() },
  { key: 'Enter', mod: true, allowInInput: true, handler: () => chatRef.value?.submit() },
  { key: 'F6', allowInInput: true, handler: () => cyclePanels(1) },
  { key: 'F6', shift: true, allowInInput: true, handler: () => cyclePanels(-1) },
])

const mobileDot = computed(() => generation.isActive)

/**
 * Panels collapse via the splitter's own API instead of v-if: the three
 * panels stay mounted (Monaco and the preview iframe survive toggling) and
 * sizes always sum to 100, which kills the "Invalid layout total size"
 * console warning the unmount approach produced.
 */
const chatPanelRef = ref<{ collapse?: () => void; expand?: () => void } | null>(null)
const previewPanelRef = ref<{ collapse?: () => void; expand?: () => void } | null>(null)

function syncPanel(panel: typeof chatPanelRef, collapsed: boolean) {
  if (collapsed) panel.value?.collapse?.()
  else panel.value?.expand?.()
}
watch(() => ui.chatCollapsed, (c) => syncPanel(chatPanelRef, c))
watch(() => ui.previewCollapsed, (c) => syncPanel(previewPanelRef, c))
onMounted(() => {
  syncPanel(chatPanelRef, ui.chatCollapsed)
  syncPanel(previewPanelRef, ui.previewCollapsed)
})
</script>

<template>
  <div class="flex h-screen flex-col bg-background">
    <!-- Loading -->
    <template v-if="state === 'loading'">
      <div class="flex h-12 items-center gap-3 border-b border-border px-3" aria-hidden="true">
        <Skeleton class="size-8 rounded-md" />
        <Skeleton class="h-5 w-40" />
      </div>
      <main id="main" class="grid flex-1 place-items-center">
        <h1 tabindex="-1" class="sr-only">Loading project</h1>
        <Loader2 class="size-5 animate-spin text-muted-foreground" aria-hidden="true" />
      </main>
    </template>

    <!-- Missing / foreign -->
    <main v-else-if="state === 'missing'" id="main" class="grid flex-1 place-items-center p-4">
      <Card class="w-full max-w-sm">
        <CardContent class="flex flex-col items-center gap-4 py-10 text-center">
          <div class="flex size-[72px] items-center justify-center rounded-xl bg-secondary" aria-hidden="true">
            <FileQuestion class="size-10 text-muted-foreground" />
          </div>
          <h1 tabindex="-1" class="text-xl font-semibold outline-none">Project not found</h1>
          <p class="text-[13px] text-muted-foreground">
            It may have been deleted, or it belongs to a different account.
          </p>
          <Button as-child>
            <RouterLink to="/projects">Back to projects</RouterLink>
          </Button>
        </CardContent>
      </Card>
    </main>

    <!-- Trashed -->
    <main v-else-if="state === 'trashed'" id="main" class="grid flex-1 place-items-center p-4">
      <Card class="w-full max-w-sm">
        <CardContent class="flex flex-col items-center gap-4 py-10 text-center">
          <div class="flex size-[72px] items-center justify-center rounded-xl bg-secondary" aria-hidden="true">
            <Trash2 class="size-10 text-muted-foreground" />
          </div>
          <h1 tabindex="-1" class="text-xl font-semibold outline-none">This project is in the trash</h1>
          <p class="text-[13px] text-muted-foreground">Restore it to keep working.</p>
          <div class="flex gap-2">
            <Button variant="secondary" as-child>
              <RouterLink to="/projects">Back to projects</RouterLink>
            </Button>
            <Button @click="workspace.restoreFromTrash()">
              <ArchiveRestore class="size-4" aria-hidden="true" /> Restore
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>

    <!-- Workspace -->
    <template v-else>
      <WorkspaceTopBar />

      <h1 tabindex="-1" class="sr-only outline-none">{{ workspace.project?.name }} workspace</h1>

      <!-- Mobile panel switcher. ToggleGroup (not Tabs): the panels are
           region wrappers, not TabsContent, so tab/tabpanel wiring would
           reference nonexistent ids. -->
      <div class="border-b border-border px-2 py-1.5 lg:hidden">
        <ToggleGroup
          :model-value="ui.mobileTab"
          type="single"
          aria-label="Workspace panel"
          class="w-full gap-1 rounded-lg bg-muted p-1"
          @update:model-value="
            (v) => {
              if (v) ui.mobileTab = v as 'chat' | 'code' | 'preview'
            }
          "
        >
          <ToggleGroupItem value="chat" class="relative h-8 flex-1 rounded-md text-[13px] data-[state=on]:bg-secondary">
            Chat
            <span
              v-if="mobileDot && ui.mobileTab !== 'chat'"
              class="genesis-activity-dot absolute top-1 right-2 size-1.5 rounded-full bg-primary"
              aria-hidden="true"
            />
            <span v-if="mobileDot && ui.mobileTab !== 'chat'" class="sr-only">(activity)</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="code" class="relative h-8 flex-1 rounded-md text-[13px] data-[state=on]:bg-secondary">
            Code
            <span
              v-if="mobileDot && ui.mobileTab !== 'code'"
              class="genesis-activity-dot absolute top-1 right-2 size-1.5 rounded-full bg-primary"
              aria-hidden="true"
            />
            <span v-if="mobileDot && ui.mobileTab !== 'code'" class="sr-only">(activity)</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="preview" class="h-8 flex-1 rounded-md text-[13px] data-[state=on]:bg-secondary">
            Preview
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      <!-- Desktop: three resizable panels -->
      <main id="main" class="relative min-h-0 flex-1">
        <div class="hidden h-full lg:block">
          <ResizablePanelGroup direction="horizontal" auto-save-id="genesis-workspace">
            <ResizablePanel
              id="chat"
              ref="chatPanelRef"
              collapsible
              :collapsed-size="0"
              :default-size="30"
              :min-size="20"
              :max-size="45"
              :order="1"
              @collapse="ui.chatCollapsed = true"
              @expand="ui.chatCollapsed = false"
            >
              <div
                data-panel-cycle="chat"
                role="region"
                tabindex="-1"
                :inert="ui.chatCollapsed"
                class="h-full overflow-hidden outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
                aria-label="Chat panel"
              >
                <ChatPanel ref="chatRef" />
              </div>
            </ResizablePanel>
            <ResizableHandle with-handle aria-label="Resize chat panel" />
            <ResizablePanel id="editor" :default-size="40" :min-size="30" :order="2">
              <div
                data-panel-cycle="editor"
                role="region"
                tabindex="-1"
                class="h-full outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
                aria-label="Editor panel"
              >
                <EditorPanel @cycle="cyclePanels" />
              </div>
            </ResizablePanel>
            <ResizableHandle with-handle aria-label="Resize preview panel" />
            <ResizablePanel
              id="preview"
              ref="previewPanelRef"
              collapsible
              :collapsed-size="0"
              :default-size="30"
              :min-size="20"
              :max-size="50"
              :order="3"
              @collapse="ui.previewCollapsed = true"
              @expand="ui.previewCollapsed = false"
            >
              <div
                data-panel-cycle="preview"
                role="region"
                tabindex="-1"
                :inert="ui.previewCollapsed"
                class="h-full overflow-hidden outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
                aria-label="Preview panel"
              >
                <PreviewPanel @focus-chat="chatRef?.focusInput()" />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>

        <!-- Mobile: one panel at a time -->
        <div class="h-full lg:hidden">
          <div
            v-show="ui.mobileTab === 'chat'"
            role="region"
            aria-label="Chat panel"
            tabindex="-1"
            class="h-full outline-none"
          >
            <ChatPanel v-if="ui.mobileTab === 'chat'" />
          </div>
          <div
            v-show="ui.mobileTab === 'code'"
            role="region"
            aria-label="Editor panel"
            tabindex="-1"
            class="h-full outline-none"
          >
            <EditorPanel @cycle="cyclePanels" />
          </div>
          <div
            v-show="ui.mobileTab === 'preview'"
            role="region"
            aria-label="Preview panel"
            tabindex="-1"
            class="h-full outline-none"
          >
            <PreviewPanel @focus-chat="ui.mobileTab = 'chat'" />
          </div>
        </div>

        <!-- Restore overlay -->
        <div
          v-if="ui.restoring"
          class="absolute inset-0 z-20 flex items-center justify-center gap-2 bg-background/80 backdrop-blur-sm"
        >
          <Loader2 class="size-4 animate-spin text-primary" aria-hidden="true" />
          <span class="text-[13px]">Restoring snapshot…</span>
        </div>
      </main>
    </template>

    <!-- Global workspace overlays -->
    <SnapshotSheet />
    <DiffDialog />
    <ConfirmActionDialog />
    <HlConnectDialog />
    <CommandPalette />
    <ShortcutsDialog />
  </div>
</template>
