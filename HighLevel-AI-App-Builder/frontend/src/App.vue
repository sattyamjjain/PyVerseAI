<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { RouterView } from 'vue-router'
import AppAnnouncer from '@/components/AppAnnouncer.vue'
import { Toaster } from '@/components/ui/sonner'

const route = useRoute()

// SPA route change: move focus to the new view's h1 (accessibility item A2).
watch(
  () => route.name,
  async (name, prev) => {
    if (prev === undefined) return // initial load keeps natural focus
    await nextTick()
    const h1 = document.querySelector<HTMLElement>('h1[tabindex="-1"]')
    h1?.focus()
  },
)
</script>

<template>
  <a href="#main" class="skip-link">Skip to main content</a>
  <AppAnnouncer />
  <RouterView />
  <Toaster theme="dark" position="bottom-right" :duration="5000" close-button />
</template>
