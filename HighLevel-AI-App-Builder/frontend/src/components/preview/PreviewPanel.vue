<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { toast } from 'vue-sonner'
import {
  Loader2,
  Monitor,
  MonitorPlay,
  RefreshCw,
  Smartphone,
  SquareTerminal,
  Terminal,
  TriangleAlert,
  Wrench,
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import PreviewConsole from '@/components/preview/PreviewConsole.vue'
import { PreviewBridge } from '@/lib/bridge'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { usePreviewStore } from '@/stores/preview'
import { useUiStore } from '@/stores/ui'
import { ariaMod } from '@/composables/useShortcuts'
import type { BridgeHlEventMessage } from '@shared/protocol'

const emit = defineEmits<{ focusChat: [] }>()

const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const preview = usePreviewStore()
const ui = useUiStore()

const iframeEl = ref<HTMLIFrameElement | null>(null)
const toolbarRefreshEl = ref<HTMLElement | null>(null)

const bridge = new PreviewBridge({
  getIframeWindow: () => iframeEl.value?.contentWindow ?? null,
  requestConfirm: (info) => ui.requestConfirm(info),
  onPreviewMessage: (msg) => preview.onPreviewMessage(msg),
})

onMounted(() => {
  bridge.start()
  if (workspace.fileContents.size > 0) rebuild()
})
onBeforeUnmount(() => bridge.stop())

function rebuild() {
  const hadFocus = document.activeElement === iframeEl.value
  preview.rebuild(workspace.fileContents, window.location.origin)
  if (hadFocus) {
    // Focus-eviction rule: the swapped iframe loses focus — land on the toolbar.
    void nextTick(() => toolbarRefreshEl.value?.focus())
  }
}

const debouncedRebuild = useDebounceFn(rebuild, 300)

// Firestore file changes rebuild the preview — but never mid-generation
// (half-written file sets render broken); one rebuild fires on completion.
watch(
  () => workspace.fileContents,
  () => {
    if (generation.isActive) return
    void debouncedRebuild()
  },
)
watch(
  () => generation.isActive,
  (active, wasActive) => {
    if (wasActive && !active) void debouncedRebuild()
  },
)

// HighLevel webhook events → toast + broadcast into the preview SDK.
const HL_EVENT_MAP: Record<string, BridgeHlEventMessage['event']> = {
  ContactCreate: 'contactCreated',
  ContactUpdate: 'contactUpdated',
  ContactDelete: 'contactDeleted',
  InboundMessage: 'inboundMessage',
  AppointmentCreate: 'appointmentCreated',
  AppointmentUpdate: 'appointmentUpdated',
}
watch(
  () => workspace.hlEvents[0]?.id,
  (id, prev) => {
    if (!id || id === prev || !workspace.hlEventsPrimed) return
    const event = workspace.hlEvents[0]!
    const mapped = HL_EVENT_MAP[event.type]
    if (mapped) {
      bridge.broadcast({ v: 1, type: 'hl.event', event: mapped, payload: event.payload })
    }
    toast(event.summary || 'CRM data changed', {
      description: 'The preview can refresh to pick up the change.',
      action: { label: 'Refresh preview', onClick: () => rebuild() },
    })
  },
)

const deviceClass = computed(() =>
  preview.deviceMode === 'mobile'
    ? 'mx-auto my-4 h-[844px] max-h-[calc(100%-2rem)] w-[390px] max-w-full rounded-lg border border-border shadow-lg'
    : 'h-full w-full',
)

function onIframeLoad() {
  preview.markLoaded()
}

function fixWithGenesis() {
  const err = preview.runtimeError
  if (!err) return
  const where = err.source ? ` in ${err.source}${err.line ? `:${err.line}` : ''}` : ''
  ui.composerPrefill = `Fix this error${where}: ${err.message}`
  preview.dismissError()
  emit('focusChat')
}

function dismissErrorOverlay() {
  preview.dismissError()
  // Focus-eviction: the overlay (and its buttons) unmount — land on the toolbar.
  void nextTick(() => toolbarRefreshEl.value?.focus())
}
</script>

<template>
  <!-- The labeled landmark is the region wrapper in WorkspaceView. -->
  <div class="flex h-full min-h-0 flex-col bg-background">
    <h2 class="sr-only">Preview</h2>

    <!-- Toolbar sits BEFORE the iframe in DOM: the keyboard escape point. -->
    <div class="flex h-10 shrink-0 items-center gap-1 border-b border-border px-2">
      <Tooltip>
        <TooltipTrigger as-child>
          <button
            ref="toolbarRefreshEl"
            type="button"
            class="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="Refresh preview"
            @click="rebuild"
          >
            <RefreshCw class="size-4" :class="{ 'animate-spin': preview.updating }" aria-hidden="true" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Refresh preview</TooltipContent>
      </Tooltip>

      <div class="flex-1" />

      <ToggleGroup
        :model-value="preview.deviceMode"
        type="single"
        size="sm"
        aria-label="Preview device size"
        @update:model-value="preview.deviceMode = ($event as 'desktop' | 'mobile') || 'desktop'"
      >
        <ToggleGroupItem value="desktop" aria-label="Desktop width" class="size-7 p-0">
          <Monitor class="size-4" aria-hidden="true" />
        </ToggleGroupItem>
        <ToggleGroupItem value="mobile" aria-label="Mobile width" class="size-7 p-0">
          <Smartphone class="size-4" aria-hidden="true" />
        </ToggleGroupItem>
      </ToggleGroup>

      <div class="flex-1" />

      <Tooltip>
        <TooltipTrigger as-child>
          <button
            type="button"
            class="relative flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            :aria-label="`Toggle console${preview.errorCount ? `, ${preview.errorCount} errors` : ''}`"
            :aria-keyshortcuts="`${ariaMod}+J`"
            @click="preview.consoleOpen = !preview.consoleOpen"
          >
            <SquareTerminal class="size-4" aria-hidden="true" />
            <Badge
              v-if="preview.errorCount > 0"
              variant="destructive"
              class="absolute -top-1 -right-1 size-4 justify-center rounded-full p-0 text-[9px]"
              aria-hidden="true"
            >
              {{ preview.errorCount > 9 ? '9+' : preview.errorCount }}
            </Badge>
          </button>
        </TooltipTrigger>
        <TooltipContent>Console</TooltipContent>
      </Tooltip>
    </div>

    <!-- Stage -->
    <div class="relative min-h-0 flex-1 overflow-auto bg-background" tabindex="-1">
      <!-- Empty state -->
      <div
        v-if="!preview.hasBuilt"
        class="flex h-full flex-col items-center justify-center gap-3 text-center"
      >
        <MonitorPlay class="size-10 text-muted-foreground/50" aria-hidden="true" />
        <div>
          <p class="text-[13px] font-medium">Nothing to preview yet</p>
          <p class="mt-0.5 text-xs text-muted-foreground">
            Your app appears here after the first generation.
          </p>
        </div>
      </div>

      <template v-else>
        <iframe
          :key="preview.srcdocKey"
          ref="iframeEl"
          :srcdoc="preview.srcdoc"
          sandbox="allow-scripts"
          title="App preview"
          referrerpolicy="no-referrer"
          allow=""
          class="block border-0 bg-white"
          :class="deviceClass"
          @load="onIframeLoad"
        />

        <!-- Updating overlay -->
        <div
          v-if="preview.updating"
          class="absolute inset-0 flex items-center justify-center gap-2 bg-background/80 backdrop-blur-sm"
        >
          <Loader2 class="size-4 animate-spin text-primary" aria-hidden="true" />
          <span class="text-[13px] text-muted-foreground">Updating preview…</span>
        </div>

        <!-- Runtime error overlay -->
        <div
          v-if="preview.runtimeError"
          class="absolute inset-x-4 bottom-4 rounded-lg border border-warning/40 bg-popover p-4 shadow-lg"
          role="group"
          aria-label="Preview runtime error"
        >
          <div class="flex items-start gap-2">
            <TriangleAlert class="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
            <div class="min-w-0 flex-1">
              <p class="text-[13px] font-medium">Runtime error in preview</p>
              <p class="mt-0.5 truncate font-mono text-xs text-muted-foreground">
                {{ preview.runtimeError.message }}
              </p>
            </div>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <Button size="sm" @click="fixWithGenesis">
              <Wrench class="size-3.5" aria-hidden="true" /> Fix with Genesis
            </Button>
            <Button size="sm" variant="ghost" @click="preview.consoleOpen = true">
              <Terminal class="size-3.5" aria-hidden="true" /> Open console
            </Button>
            <Button size="sm" variant="ghost" @click="dismissErrorOverlay">Dismiss</Button>
          </div>
        </div>
      </template>
    </div>

    <PreviewConsole />
  </div>
</template>
