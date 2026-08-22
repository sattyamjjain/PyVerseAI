<script setup lang="ts">
import { computed, ref } from 'vue'
import { Copy, Sparkles, User } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import ChatMarkdown from '@/components/chat/ChatMarkdown.vue'
import GenerationActivityCard from '@/components/chat/GenerationActivityCard.vue'
import { absoluteTime } from '@/lib/time'
import type { MessageRow } from '@/stores/workspace'

const props = defineProps<{ message: MessageRow }>()

const isAssistant = computed(() => props.message.role === 'assistant')

/** Persisted assistant turns end with LLM-history stubs like
 *  "[wrote app.js (4.4 KB)]" — context for the model, noise for humans. */
const displayContent = computed(() =>
  isAssistant.value
    ? props.message.content.replace(/(\s*\[(?:wrote|deleted) [^\]]*\])+\s*$/, '').trimEnd()
    : props.message.content,
)
const hovering = ref(false)

async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    toast('Copied to clipboard')
  } catch {
    toast.error('Copy failed')
  }
}
</script>

<template>
  <article
    class="group relative"
    @mouseenter="hovering = true"
    @mouseleave="hovering = false"
  >
    <header class="mb-1.5 flex items-center gap-1.5">
      <Sparkles v-if="isAssistant" class="size-4 text-primary" aria-hidden="true" />
      <User v-else class="size-4 text-muted-foreground" aria-hidden="true" />
      <Tooltip>
        <TooltipTrigger as-child>
          <span tabindex="0" class="rounded-sm text-xs font-medium text-muted-foreground">
            <span class="sr-only">{{ isAssistant ? 'Genesis:' : 'You:' }}</span>
            <span aria-hidden="true">{{ isAssistant ? 'Genesis' : 'You' }}</span>
            <span class="sr-only">, {{ absoluteTime(message.createdAt) }}</span>
          </span>
        </TooltipTrigger>
        <TooltipContent>{{ absoluteTime(message.createdAt) }}</TooltipContent>
      </Tooltip>
      <button
        v-if="isAssistant"
        type="button"
        class="ml-auto flex size-6 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100"
        aria-label="Copy message"
        @click="copyContent"
      >
        <Copy class="size-3.5" aria-hidden="true" />
      </button>
    </header>

    <div v-if="isAssistant" class="space-y-3">
      <ChatMarkdown v-if="displayContent" :source="displayContent" />
      <GenerationActivityCard v-if="message.meta" mode="persisted" :meta="message.meta" />
      <p v-if="message.meta?.error" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive-soft">
        {{ message.meta.error }}
      </p>
    </div>
    <div v-else class="rounded-lg bg-secondary px-3 py-2 text-[14px] leading-[1.65] whitespace-pre-wrap">{{ message.content }}</div>
  </article>
</template>
