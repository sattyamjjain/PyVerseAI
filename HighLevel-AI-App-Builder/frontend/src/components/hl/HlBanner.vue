<script setup lang="ts">
import { ref } from 'vue'
import { X, Zap } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()

const dismissed = ref(sessionStorage.getItem('genesis:hl-banner-dismissed') === 'true')

function dismiss() {
  dismissed.value = true
  sessionStorage.setItem('genesis:hl-banner-dismissed', 'true')
}
</script>

<template>
  <div
    v-if="!auth.hlConnected && !dismissed"
    class="flex items-center gap-3 rounded-xl border border-warning/30 bg-warning/5 px-4 py-3"
  >
    <div
      class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-warning/10"
      aria-hidden="true"
    >
      <Zap class="size-4 text-warning" />
    </div>
    <p class="min-w-0 flex-1 text-[13px] leading-snug">
      <span class="font-medium">Connect your HighLevel account.</span>
      <span class="text-muted-foreground">
        Genesis needs a HighLevel location to generate working CRM apps.</span
      >
    </p>
    <Button size="sm" @click="ui.hlDialogOpen = true">Connect HighLevel</Button>
    <button
      type="button"
      class="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground"
      aria-label="Dismiss for this session"
      @click="dismiss"
    >
      <X class="size-4" aria-hidden="true" />
    </button>
  </div>
</template>
