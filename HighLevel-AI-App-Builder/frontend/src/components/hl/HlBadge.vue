<script setup lang="ts">
import { computed } from 'vue'
import { Plug } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

defineProps<{ compact?: boolean }>()

const auth = useAuthStore()
const ui = useUiStore()

const state = computed<'connected' | 'reconnect' | 'none'>(() => {
  if (auth.hl?.status === 'connected') return 'connected'
  if (auth.hl?.status === 'needs_reconnect') return 'reconnect'
  return 'none'
})

const label = computed(() => {
  if (state.value === 'connected') return auth.hl?.locationName || 'Connected'
  if (state.value === 'reconnect') return 'Reconnect HighLevel'
  return 'Connect HighLevel'
})
</script>

<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <button
        type="button"
        class="flex h-7 min-w-0 items-center gap-2 rounded-full border border-border bg-secondary/70 px-3 text-xs font-medium text-foreground transition-colors duration-150 hover:bg-accent"
        :aria-label="`HighLevel connection: ${label}`"
        @click="ui.hlDialogOpen = true"
      >
        <span
          class="size-1.5 shrink-0 rounded-full"
          :class="{
            'bg-success': state === 'connected',
            'bg-warning': state === 'reconnect',
            'bg-muted-foreground': state === 'none',
          }"
        />
        <Plug v-if="state === 'none' && compact" class="size-3.5" aria-hidden="true" />
        <span v-if="!compact" class="max-w-40 truncate">{{ label }}</span>
      </button>
    </TooltipTrigger>
    <TooltipContent>{{ label }}</TooltipContent>
  </Tooltip>
</template>
