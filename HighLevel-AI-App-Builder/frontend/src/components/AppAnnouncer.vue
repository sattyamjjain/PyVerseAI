<script setup lang="ts">
// The single live-region announcer — mounted once in App.vue, never v-if'd
// (freshly-inserted live regions drop announcements in VoiceOver).
import { useAnnouncerState } from '@/composables/useAnnouncer'

const { politeText, alertText } = useAnnouncerState()
</script>

<template>
  <div class="sr-only">
    <div role="status" aria-atomic="true">{{ politeText }}</div>
    <div role="alert">{{ alertText }}</div>
  </div>
</template>
