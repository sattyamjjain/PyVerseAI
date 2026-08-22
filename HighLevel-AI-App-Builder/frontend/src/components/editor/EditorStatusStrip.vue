<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, Loader2, Lock } from 'lucide-vue-next'
import { languageForPath } from '@/lib/monaco'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'

const props = defineProps<{ line: number; col: number }>()

const workspace = useWorkspaceStore()
const generation = useGenerationStore()

const savedFlash = ref(false)
watch(
  () => workspace.lastSavedAt,
  () => {
    savedFlash.value = true
    setTimeout(() => (savedFlash.value = false), 1500)
  },
)

const saving = computed(() => workspace.savingPaths.size > 0)
const language = computed(() =>
  workspace.activePath ? languageForPath(workspace.activePath) : '',
)
</script>

<template>
  <div
    class="flex h-7 items-center gap-3 border-t border-border bg-background px-3 font-mono text-[11px] text-muted-foreground"
  >
    <span class="min-w-0 flex-1 truncate">{{ workspace.activePath ?? '' }}</span>
    <span v-if="generation.isActive" class="flex items-center gap-1 text-primary">
      <Lock class="size-3" aria-hidden="true" /> read-only
    </span>
    <span v-if="saving" class="flex items-center gap-1">
      <Loader2 class="size-3 animate-spin" aria-hidden="true" /> Saving
    </span>
    <span v-else-if="savedFlash" class="flex items-center gap-1 text-success">
      <Check class="size-3" aria-hidden="true" /> Saved
    </span>
    <span v-if="language">{{ language }}</span>
    <span v-if="workspace.activePath">Ln {{ props.line }}, Col {{ props.col }}</span>
  </div>
</template>
