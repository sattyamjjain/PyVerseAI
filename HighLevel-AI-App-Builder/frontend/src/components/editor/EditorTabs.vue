<script setup lang="ts">
import { nextTick } from 'vue'
import { Crosshair, PanelLeft, X } from 'lucide-vue-next'
import { Toggle } from '@/components/ui/toggle'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { useUiStore } from '@/stores/ui'

defineProps<{ treeVisible: boolean }>()
const emit = defineEmits<{ toggleTree: [] }>()

const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const ui = useUiStore()

function activate(path: string) {
  workspace.activePath = path
  if (generation.isActive) ui.followMode = false // manual navigation disarms follow
}

async function close(path: string) {
  workspace.closeTab(path)
  await nextTick()
  // Focus-eviction: land on the now-active tab, else the tab bar container.
  const nextTab = workspace.activePath
    ? document.querySelector<HTMLElement>(`[data-tab-path="${CSS.escape(workspace.activePath)}"]`)
    : null
  ;(nextTab ?? document.querySelector<HTMLElement>('[data-editor-tabbar]'))?.focus()
}

function rearmFollow() {
  ui.followMode = !ui.followMode
  if (ui.followMode && generation.streamingPath) {
    workspace.openFile(generation.streamingPath)
  }
}
</script>

<template>
  <div
    data-editor-tabbar
    tabindex="-1"
    class="flex h-9 items-center border-b border-border bg-background"
  >
    <Tooltip>
      <TooltipTrigger as-child>
        <button
          type="button"
          class="flex size-9 shrink-0 items-center justify-center border-r border-border text-muted-foreground hover:bg-accent hover:text-foreground"
          :aria-label="treeVisible ? 'Hide file tree' : 'Show file tree'"
          :aria-expanded="treeVisible"
          @click="emit('toggleTree')"
        >
          <PanelLeft class="size-4" aria-hidden="true" />
        </button>
      </TooltipTrigger>
      <TooltipContent>{{ treeVisible ? 'Hide' : 'Show' }} file tree</TooltipContent>
    </Tooltip>

    <div role="tablist" aria-label="Open files" class="flex min-w-0 flex-1 items-center overflow-x-auto">
      <!-- Tab select and close are SIBLING buttons (no nested interactives). -->
      <div
        v-for="path in workspace.openTabs"
        :key="path"
        class="group flex h-9 shrink-0 items-stretch border-r border-border transition-colors"
        :class="
          workspace.activePath === path
            ? 'bg-editor text-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-foreground'
        "
      >
        <button
          role="tab"
          type="button"
          :data-tab-path="path"
          :aria-selected="workspace.activePath === path"
          class="flex items-center gap-1.5 pr-1 pl-3 font-mono text-xs"
          @click="activate(path)"
        >
          <span
            v-if="workspace.dirtyPaths.has(path)"
            class="size-1.5 rounded-full bg-primary"
            aria-hidden="true"
          />
          {{ path.split('/').pop() }}
        </button>
        <button
          type="button"
          class="flex w-6 items-center justify-center opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100"
          :aria-label="`Close ${path}`"
          @click="close(path)"
        >
          <span class="flex size-4 items-center justify-center rounded hover:bg-secondary">
            <X class="size-3" aria-hidden="true" />
          </span>
        </button>
      </div>
    </div>

    <Tooltip>
      <TooltipTrigger as-child>
        <Toggle
          :model-value="ui.followMode"
          size="sm"
          class="mr-1 size-7 shrink-0 p-0"
          aria-label="Follow generation stream"
          @update:model-value="rearmFollow"
        >
          <Crosshair class="size-4" aria-hidden="true" />
        </Toggle>
      </TooltipTrigger>
      <TooltipContent>Follow the stream</TooltipContent>
    </Tooltip>
  </div>
</template>
