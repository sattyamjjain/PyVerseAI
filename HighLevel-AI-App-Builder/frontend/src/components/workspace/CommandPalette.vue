<script setup lang="ts">
import {
  Camera,
  Database,
  FileCode2,
  Keyboard,
  MessageSquare,
  Monitor,
  Plug,
  Smartphone,
  Square,
  SquareTerminal,
} from 'lucide-vue-next'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { callFn } from '@/lib/api'
import { toast } from 'vue-sonner'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { usePreviewStore } from '@/stores/preview'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const preview = usePreviewStore()
const ui = useUiStore()
const auth = useAuthStore()

function run(action: () => void) {
  ui.paletteOpen = false
  action()
}

async function seed() {
  try {
    const res = await callFn<{ seeded: { contacts: number } }>('seedSandbox', {})
    toast.success(`Seeded demo data (${res.seeded.contacts} contacts)`)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Seeding failed')
  }
}
</script>

<template>
  <CommandDialog v-model:open="ui.paletteOpen" title="Command palette" description="Search commands and files">
    <CommandInput placeholder="Type a command or file name…" />
    <CommandList>
      <CommandEmpty>No results.</CommandEmpty>
      <CommandGroup v-if="workspace.filePaths.length" heading="Files">
        <CommandItem
          v-for="path in workspace.filePaths"
          :key="path"
          :value="`open ${path}`"
          @select="run(() => workspace.openFile(path))"
        >
          <FileCode2 class="size-4" aria-hidden="true" />
          <span class="font-mono text-xs">{{ path }}</span>
        </CommandItem>
      </CommandGroup>
      <CommandSeparator v-if="workspace.filePaths.length" />
      <CommandGroup heading="Actions">
        <CommandItem
          v-if="generation.isActive"
          value="stop generation"
          @select="run(() => generation.cancel())"
        >
          <Square class="size-4" aria-hidden="true" /> Stop generation
        </CommandItem>
        <CommandItem value="snapshot history" @select="run(() => (ui.snapshotSheetOpen = true))">
          <Camera class="size-4" aria-hidden="true" /> Snapshot history
        </CommandItem>
        <CommandItem value="toggle chat panel" @select="run(() => (ui.chatCollapsed = !ui.chatCollapsed))">
          <MessageSquare class="size-4" aria-hidden="true" /> Toggle chat panel
        </CommandItem>
        <CommandItem
          value="toggle preview console"
          @select="run(() => (preview.consoleOpen = !preview.consoleOpen))"
        >
          <SquareTerminal class="size-4" aria-hidden="true" /> Toggle preview console
        </CommandItem>
        <CommandItem
          value="switch device mode"
          @select="run(() => (preview.deviceMode = preview.deviceMode === 'desktop' ? 'mobile' : 'desktop'))"
        >
          <component
            :is="preview.deviceMode === 'desktop' ? Smartphone : Monitor"
            class="size-4"
            aria-hidden="true"
          />
          Switch to {{ preview.deviceMode === 'desktop' ? 'mobile' : 'desktop' }} preview
        </CommandItem>
        <CommandItem value="connect highlevel" @select="run(() => (ui.hlDialogOpen = true))">
          <Plug class="size-4" aria-hidden="true" /> HighLevel connection
        </CommandItem>
        <CommandItem
          v-if="auth.hlConnected"
          value="seed demo data"
          @select="run(() => void seed())"
        >
          <Database class="size-4" aria-hidden="true" /> Seed demo data
        </CommandItem>
        <CommandItem value="keyboard shortcuts" @select="run(() => (ui.shortcutsOpen = true))">
          <Keyboard class="size-4" aria-hidden="true" /> Keyboard shortcuts
        </CommandItem>
      </CommandGroup>
    </CommandList>
  </CommandDialog>
</template>
