<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowDown, Info, Sparkles } from 'lucide-vue-next'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatMarkdown from '@/components/chat/ChatMarkdown.vue'
import GenerationActivityCard from '@/components/chat/GenerationActivityCard.vue'
import PromptComposer from '@/components/chat/PromptComposer.vue'
import SuggestionChips from '@/components/chat/SuggestionChips.vue'
import { Button } from '@/components/ui/button'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'

const workspace = useWorkspaceStore()
const generation = useGenerationStore()

const scrollEl = ref<HTMLElement | null>(null)
const composerRef = ref<InstanceType<typeof PromptComposer> | null>(null)
const pinned = ref(true)
const interruptedDismissed = ref(false)

const showLiveEntry = computed(() => generation.phase !== 'idle')

/** Hide the persisted twin of the live entry until the user settles it. */
const visibleMessages = computed(() => {
  if (!showLiveEntry.value || !generation.activeGenerationId) return workspace.messages
  return workspace.messages.filter(
    (m) => !(m.role === 'assistant' && m.generationId === generation.activeGenerationId),
  )
})

const interruptedGeneration = computed(() => {
  if (interruptedDismissed.value || generation.phase !== 'idle') return null
  const latest = workspace.latestGeneration
  if (!latest || latest.status !== 'running') return null
  if (latest.id === generation.activeGenerationId) return null
  return latest
})

const isEmpty = computed(
  () => workspace.messages.length === 0 && generation.phase === 'idle',
)

function onScroll() {
  const el = scrollEl.value
  if (!el) return
  pinned.value = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}

async function scrollToBottom(force = false) {
  await nextTick()
  const el = scrollEl.value
  if (!el) return
  if (pinned.value || force) {
    el.scrollTop = el.scrollHeight
    pinned.value = true
  }
}

watch(
  () => [
    workspace.messages.length,
    generation.narration.length,
    generation.liveFiles.length,
    generation.phase,
  ],
  () => void scrollToBottom(),
)

// When the persisted assistant message lands after success, settle the live UI.
watch(
  () => workspace.messages.length,
  () => {
    if (generation.phase !== 'done' && generation.phase !== 'stopped') return
    const gid = generation.activeGenerationId
    if (gid && workspace.messages.some((m) => m.role === 'assistant' && m.generationId === gid)) {
      generation.settle()
    }
  },
)

function continueGeneration() {
  generation.reset()
  void generation.send('Continue where you left off — finish the remaining files.')
}

defineExpose({
  focusInput: () => composerRef.value?.focusInput(),
  submit: () => composerRef.value?.submit(),
})
</script>

<template>
  <section class="flex h-full min-h-0 flex-col" aria-label="Chat">
    <h2 class="sr-only">Chat</h2>

    <div
      ref="scrollEl"
      class="relative min-h-0 flex-1 overflow-y-auto px-4 py-4"
      tabindex="-1"
      @scroll.passive="onScroll"
    >
      <!-- Empty state -->
      <div v-if="isEmpty" class="flex h-full flex-col items-center justify-center gap-4 text-center">
        <div class="flex size-[72px] items-center justify-center rounded-xl bg-secondary" aria-hidden="true">
          <Sparkles class="size-10 text-primary" />
        </div>
        <div>
          <p class="text-[15px] font-semibold">Describe your first app</p>
          <p class="mt-1 text-[13px] text-muted-foreground">
            Genesis turns plain English into a working HighLevel app.
          </p>
        </div>
        <SuggestionChips />
      </div>

      <div v-else class="space-y-5">
        <!-- Interrupted-generation notice -->
        <div
          v-if="interruptedGeneration"
          class="flex items-start gap-2 rounded-lg border border-info/40 bg-info/10 px-3 py-2"
        >
          <Info class="mt-0.5 size-4 shrink-0 text-info" aria-hidden="true" />
          <div class="min-w-0 flex-1">
            <p class="text-[13px]">
              A generation was interrupted —
              {{ interruptedGeneration.filesWritten.length }}
              {{ interruptedGeneration.filesWritten.length === 1 ? 'file' : 'files' }} landed safely.
            </p>
          </div>
          <Button size="sm" variant="ghost" @click="interruptedDismissed = true">Dismiss</Button>
        </div>

        <ChatMessage v-for="message in visibleMessages" :key="message.id" :message="message" />

        <!-- Live streaming assistant entry -->
        <article v-if="showLiveEntry">
          <header class="mb-1.5 flex items-center gap-1.5">
            <Sparkles class="size-4 text-primary" aria-hidden="true" />
            <span class="text-xs font-medium text-muted-foreground">
              <span class="sr-only">Genesis:</span>
              <span aria-hidden="true">Genesis</span>
            </span>
          </header>
          <div class="space-y-3">
            <p
              v-if="!generation.narration && ['sending', 'planning'].includes(generation.phase)"
              class="genesis-shimmer w-fit text-[14px]"
            >
              Thinking…
            </p>
            <ChatMarkdown
              v-if="generation.narration"
              :source="generation.narration"
              :streaming="generation.isActive"
            />
            <GenerationActivityCard
              v-if="generation.liveFiles.length || ['failed', 'stopped'].includes(generation.phase)"
              mode="live"
              @continue-gen="continueGeneration"
              @dismiss="generation.reset()"
            />
          </div>
        </article>

      </div>

      <!-- Jump to latest -->
      <div v-if="!pinned" class="pointer-events-none sticky bottom-2 flex justify-center">
        <Button
          size="sm"
          variant="secondary"
          class="pointer-events-auto shadow-lg"
          @click="scrollToBottom(true)"
        >
          <ArrowDown class="size-3.5" aria-hidden="true" /> Jump to latest
        </Button>
      </div>
    </div>

    <PromptComposer ref="composerRef" />
  </section>
</template>
