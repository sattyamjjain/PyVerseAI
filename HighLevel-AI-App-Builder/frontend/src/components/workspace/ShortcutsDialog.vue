<script setup lang="ts">
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { useUiStore } from '@/stores/ui'
import { isMac, modKeyLabel } from '@/composables/useShortcuts'

const ui = useUiStore()

const groups = [
  {
    title: 'General',
    items: [
      { keys: [modKeyLabel, 'K'], label: 'Command palette' },
      { keys: [modKeyLabel, '⏎'], label: 'Send prompt' },
      { keys: ['⏎'], label: 'Send prompt (from the chat input)' },
      { keys: ['⇧', '⏎'], label: 'New line in the chat input' },
      { keys: [modKeyLabel, '.'], label: 'Stop generation' },
      { keys: ['Esc'], label: 'Close the open dialog or sheet' },
    ],
  },
  {
    title: 'Workspace',
    items: [
      { keys: [modKeyLabel, 'S'], label: 'Save the active file' },
      { keys: [modKeyLabel, 'B'], label: 'Toggle the chat panel' },
      { keys: [modKeyLabel, 'J'], label: 'Toggle the preview console' },
      { keys: ['F6'], label: 'Move focus to the next panel' },
      { keys: ['⇧', 'F6'], label: 'Move focus to the previous panel' },
    ],
  },
  {
    title: 'Inside the code editor (Monaco)',
    items: [
      { keys: [isMac ? '⌃⇧M' : 'Ctrl+M'], label: 'Toggle Tab-moves-focus mode' },
      { keys: ['⌥', 'F1'], label: 'Open editor accessibility help' },
      { keys: [modKeyLabel, 'S'], label: 'Save (also works inside the editor)' },
      { keys: ['F6'], label: 'Leave the editor to the next panel' },
    ],
  },
]
</script>

<template>
  <Dialog v-model:open="ui.shortcutsOpen">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Keyboard shortcuts</DialogTitle>
        <DialogDescription>Every shortcut also has a visible on-screen control.</DialogDescription>
      </DialogHeader>
      <div class="space-y-4">
        <template v-for="(group, gi) in groups" :key="group.title">
          <Separator v-if="gi > 0" />
          <div>
            <h3 class="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {{ group.title }}
            </h3>
            <ul class="space-y-1.5">
              <li
                v-for="item in group.items"
                :key="item.label"
                class="flex items-center justify-between gap-4"
              >
                <span class="text-[13px]">{{ item.label }}</span>
                <span class="flex shrink-0 gap-1">
                  <kbd
                    v-for="key in item.keys"
                    :key="key"
                    class="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground"
                    >{{ key }}</kbd
                  >
                </span>
              </li>
            </ul>
          </div>
        </template>
      </div>
    </DialogContent>
  </Dialog>
</template>
