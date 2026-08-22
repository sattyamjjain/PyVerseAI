<script setup lang="ts">
import { Calendar, MessageSquare, Users } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const ui = useUiStore()
const auth = useAuthStore()

const chips = [
  {
    icon: Users,
    label: 'Contact dashboard with search',
    prompt:
      'Build a contact dashboard that shows my contacts in a searchable, sortable table with name, email, phone and tags, plus a detail panel when I click a contact.',
  },
  {
    icon: MessageSquare,
    label: 'Conversation inbox viewer',
    prompt:
      'Build a conversation inbox that lists my recent conversations with unread indicators, and shows the full message thread when I select one.',
  },
  {
    icon: Calendar,
    label: 'Appointment calendar overview',
    prompt:
      'Build an appointment overview that shows my upcoming appointments for the next 14 days grouped by day, with the contact name, time, and status for each.',
  },
]

function insert(prompt: string) {
  if (!auth.hlConnected) return
  ui.composerPrefill = prompt
}
</script>

<template>
  <div class="flex flex-wrap justify-center gap-2">
    <button
      v-for="chip in chips"
      :key="chip.label"
      type="button"
      class="flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary/40 hover:bg-accent"
      :class="{ 'pointer-events-none opacity-50': !auth.hlConnected }"
      :aria-disabled="!auth.hlConnected || undefined"
      :aria-describedby="!auth.hlConnected ? 'composer-blocked-reason' : undefined"
      @click="insert(chip.prompt)"
    >
      <component :is="chip.icon" class="size-3.5 text-primary" aria-hidden="true" />
      {{ chip.label }}
    </button>
  </div>
</template>
