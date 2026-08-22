<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowUp, Square, TriangleAlert, Zap } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import { useGenerationStore } from '@/stores/generation'
import { useUiStore } from '@/stores/ui'

const MAX_CHARS = 4000
const WARN_AT = 3500

const auth = useAuthStore()
const generation = useGenerationStore()
const ui = useUiStore()

const draft = ref('')
const textareaEl = ref<HTMLTextAreaElement | null>(null)
const sendButtonEl = ref<HTMLElement | null>(null)

const streaming = computed(() => generation.isActive)
const blocked = computed(() => !auth.hlConnected)
const overLimit = computed(() => draft.value.length > MAX_CHARS)
const canSend = computed(
  () => !blocked.value && !streaming.value && draft.value.trim().length > 0 && !overLimit.value,
)

// External prefill ("Fix with Genesis", suggestion chips).
watch(
  () => ui.composerPrefill,
  async (text) => {
    if (text === null) return
    draft.value = text
    ui.composerPrefill = null
    await nextTick()
    textareaEl.value?.focus()
    autogrow()
  },
)

// Focus-eviction rule: when Stop morphs back to Send, keep focus in the composer.
watch(streaming, async (now, was) => {
  if (was && !now) {
    await nextTick()
    if (document.activeElement === document.body) textareaEl.value?.focus()
  }
})

function autogrow() {
  const el = textareaEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(160, Math.max(44, el.scrollHeight)) + 'px'
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Enter') return
  if (e.isComposing) return
  if (e.shiftKey) return // newline
  e.preventDefault()
  submit()
}

function submit() {
  if (!canSend.value) return
  const prompt = draft.value.trim()
  draft.value = ''
  nextTick(() => autogrow())
  void generation.send(prompt)
}

defineExpose({
  focusInput: () => textareaEl.value?.focus(),
  submit,
})
</script>

<template>
  <div class="border-t border-border p-3">
    <!-- Blocked reason (never opacity alone) -->
    <div
      v-if="blocked"
      id="composer-blocked-reason"
      class="mb-2 flex items-center gap-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2"
    >
      <TriangleAlert class="size-4 shrink-0 text-warning" aria-hidden="true" />
      <p class="min-w-0 flex-1 text-[13px]">
        Connect HighLevel to generate — generated apps call the HighLevel API through your
        connection.
      </p>
      <Button size="sm" variant="secondary" @click="ui.hlDialogOpen = true">Connect</Button>
    </div>

    <div
      class="rounded-lg border border-border bg-card transition-colors focus-within:border-primary/60"
    >
      <textarea
        id="prompt-input"
        ref="textareaEl"
        v-model="draft"
        class="block max-h-40 min-h-11 w-full resize-none bg-transparent px-3 pt-2.5 text-[13px] leading-relaxed outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed"
        :placeholder="
          streaming ? 'Waiting for generation to finish…' : 'Describe the app you want to build…'
        "
        aria-label="Message Genesis"
        aria-describedby="composer-hint"
        :aria-disabled="blocked || undefined"
        :disabled="streaming"
        :maxlength="MAX_CHARS + 100"
        rows="1"
        @input="autogrow"
        @keydown="onKeydown"
      />
      <div class="flex items-center justify-between gap-2 px-2 pb-2">
        <div class="flex items-center gap-2">
          <Select
            :model-value="generation.model"
            @update:model-value="generation.setModel($event as 'fast' | 'best')"
          >
            <SelectTrigger
              class="h-7 w-auto gap-1.5 border-none bg-transparent px-2 text-xs text-muted-foreground hover:bg-accent"
              aria-label="Generation model"
            >
              <Zap class="size-3.5" aria-hidden="true" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="fast">Fast — Sonnet</SelectItem>
              <SelectItem value="best">Best — Opus</SelectItem>
            </SelectContent>
          </Select>
          <span
            v-if="draft.length >= WARN_AT"
            class="font-mono text-[11px]"
            :class="overLimit ? 'text-destructive-soft' : 'text-warning'"
            role="status"
          >
            {{ draft.length.toLocaleString() }} / {{ MAX_CHARS.toLocaleString() }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span id="composer-hint" class="hidden text-[11px] text-muted-foreground xl:block">
            ⏎ Send · ⇧⏎ New line
          </span>
          <Button
            v-if="streaming"
            ref="sendButtonEl"
            size="icon"
            variant="outline"
            class="size-8 border-destructive/50 text-destructive-soft hover:bg-destructive/10"
            aria-label="Stop generation"
            aria-keyshortcuts="Meta+Period"
            @click="generation.cancel()"
          >
            <Square class="size-3.5" aria-hidden="true" />
          </Button>
          <Button
            v-else
            ref="sendButtonEl"
            size="icon"
            class="size-8"
            :disabled="!canSend"
            :aria-disabled="!canSend || undefined"
            :aria-describedby="blocked ? 'composer-blocked-reason' : undefined"
            aria-label="Send message"
            aria-keyshortcuts="Enter Meta+Enter"
            @click="submit"
          >
            <ArrowUp class="size-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
