<script setup lang="ts">
import { computed } from 'vue'
import { CircleAlert, CircleSlash, Check } from 'lucide-vue-next'
import { useGenerationStore } from '@/stores/generation'

const generation = useGenerationStore()

const visible = computed(() => generation.phase !== 'idle')
const tone = computed(() => {
  switch (generation.phase) {
    case 'done':
      return 'success'
    case 'failed':
      return 'error'
    case 'stopped':
      return 'muted'
    default:
      return 'active'
  }
})
</script>

<template>
  <!-- Screen readers get these transitions via the app announcer, not here. -->
  <div
    v-if="visible"
    aria-hidden="true"
    class="flex h-7 max-w-72 items-center gap-2 rounded-full bg-secondary px-3 text-xs font-medium"
    :class="{
      'text-foreground shadow-[0_0_12px_oklch(0.83_0.19_84/0.25)]': tone === 'active',
      'text-success': tone === 'success',
      'text-destructive-soft': tone === 'error',
      'text-muted-foreground': tone === 'muted',
    }"
  >
    <span
      v-if="tone === 'active'"
      class="genesis-activity-dot size-1.5 shrink-0 rounded-full bg-primary"
    />
    <Check v-else-if="tone === 'success'" class="size-3.5 shrink-0" />
    <CircleAlert v-else-if="tone === 'error'" class="size-3.5 shrink-0" />
    <CircleSlash v-else class="size-3.5 shrink-0" />
    <span class="truncate font-mono">{{ generation.pillText }}</span>
  </div>
</template>
