<script setup lang="ts">
import { ref } from 'vue'
import { Sparkles } from 'lucide-vue-next'

defineProps<{ src: string; alt: string }>()

const loaded = ref(false)
const failed = ref(false)
</script>

<template>
  <div class="relative aspect-video w-full overflow-hidden bg-editor">
    <img
      v-if="!failed"
      :src="src"
      :alt="alt"
      loading="lazy"
      class="block h-full w-full object-cover object-top transition-opacity duration-200"
      :class="loaded ? 'opacity-100' : 'opacity-0'"
      @load="loaded = true"
      @error="failed = true"
    />
    <!-- Placeholder until the capture lands (or if it is missing). -->
    <div
      v-if="!loaded"
      class="absolute inset-0 flex items-center justify-center"
      aria-hidden="true"
    >
      <Sparkles class="size-8 text-border" />
    </div>
  </div>
</template>
