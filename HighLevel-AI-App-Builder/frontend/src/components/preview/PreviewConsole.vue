<script setup lang="ts">
import { computed } from 'vue'
import { Ban, ChevronDown, ChevronUp, CircleAlert, Info, TriangleAlert } from 'lucide-vue-next'
import { usePreviewStore } from '@/stores/preview'

const preview = usePreviewStore()

const summary = computed(() => {
  const parts: string[] = []
  if (preview.errorCount) parts.push(`${preview.errorCount} error${preview.errorCount === 1 ? '' : 's'}`)
  if (preview.warnCount) parts.push(`${preview.warnCount} warning${preview.warnCount === 1 ? '' : 's'}`)
  return parts.length ? parts.join(' · ') : 'Console'
})

function iconFor(level: string) {
  if (level === 'error') return CircleAlert
  if (level === 'warn') return TriangleAlert
  return Info
}
function prefixFor(level: string) {
  if (level === 'error') return 'Error: '
  if (level === 'warn') return 'Warning: '
  return ''
}
</script>

<template>
  <div class="border-t border-border bg-background" role="region" aria-label="Preview console">
    <!-- Toggle and Clear are SIBLING buttons (no nested interactives). -->
    <div class="flex h-7 items-stretch text-[11px] text-muted-foreground">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-center gap-2 px-3 hover:bg-accent"
        :aria-expanded="preview.consoleOpen"
        aria-controls="preview-console-list"
        @click="preview.consoleOpen = !preview.consoleOpen"
      >
        <component
          :is="preview.consoleOpen ? ChevronDown : ChevronUp"
          class="size-3.5"
          aria-hidden="true"
        />
        <span :class="{ 'text-destructive-soft': preview.errorCount > 0 }">{{ summary }}</span>
      </button>
      <button
        v-if="preview.consoleOpen && preview.consoleEntries.length"
        type="button"
        class="flex items-center gap-1 px-2.5 hover:bg-secondary hover:text-foreground"
        aria-label="Clear console"
        @click="preview.clearConsole()"
      >
        <Ban class="size-3" aria-hidden="true" /> Clear
      </button>
    </div>
    <div
      v-if="preview.consoleOpen"
      id="preview-console-list"
      tabindex="0"
      aria-label="Console output"
      class="h-44 overflow-y-auto border-t border-border font-mono text-xs"
    >
      <p v-if="preview.consoleEntries.length === 0" class="px-3 py-2 text-muted-foreground">
        Console output from the preview appears here.
      </p>
      <div
        v-for="(entry, i) in preview.consoleEntries"
        :key="i"
        class="flex items-start gap-2 border-b border-border/50 px-3 py-1"
        :class="{
          'text-destructive-soft': entry.level === 'error',
          'text-warning': entry.level === 'warn',
          'text-muted-foreground': entry.level === 'log' || entry.level === 'info',
        }"
      >
        <component :is="iconFor(entry.level)" class="mt-0.5 size-3 shrink-0" aria-hidden="true" />
        <span class="min-w-0 flex-1 break-words whitespace-pre-wrap">{{ prefixFor(entry.level) }}{{ entry.text }}</span>
      </div>
    </div>
  </div>
</template>
