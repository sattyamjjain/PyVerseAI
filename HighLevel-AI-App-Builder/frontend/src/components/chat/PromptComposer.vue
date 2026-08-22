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
import { announce } from '@/composables/useAnnouncer'
import { ariaMod } from '@/composables/useShortcuts'

const MAX_CHARS = 4000
const WARN_AT = 3500

const auth = useAuthStore()
const generation = useGenerationStore()
const ui = useUiStore()

const draft = ref('')
const textareaEl = ref<HTMLTextAreaElement | null>(null)
const stopButton = ref<InstanceType<typeof Button> | null>(null)

const streaming = computed(() => generation.isActive)
const blocked = computed(() => !auth.hlConnected)
const overLimit = computed(() => draft.value.length > MAX_CHARS)
const canSend = computed(
  () => !blocked.value && !streaming.value && draft.value.trim().length > 0 && !overLimit.value,
)

const describedBy = computed(() => {
  const ids = ['composer-hint']
  if (blocked.value) ids.push('composer-blocked-reason')
  if (draft.value.length >= WARN_AT) ids.push('composer-counter')
  return ids.join(' ')
})

// Character-limit announcements happen on threshold CROSSINGS only.
let limitState: 'ok' | 'warn' | 'over' = 'ok'
watch(
  () => draft.value.length,
  (len) => {
    const next = len > MAX_CHARS ? 'over' : len >= WARN_AT ? 'warn' : 'ok'
    if (next === limitState) return
    if (next === 'over') announce('Character limit reached — shorten your prompt to send')
    else if (next === 'warn' && limitState === 'ok')
      announce(`Approaching the character limit: ${len} of ${MAX_CHARS}`)
    limitState = next
  },
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

// Focus-eviction rule for the Send⇄Stop morph, both directions.
watch(streaming, async (now, was) => {
  await nextTick()
  if (!was && now) {
    // Send vanished; if focus fell to body, land on Stop.
    if (document.activeElement === document.body) stopButton.value?.$el?.focus()
  } else if (was && !now) {
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
      <!-- readonly (not disabled) while streaming: stays focusable/readable
           and the draft is preserved. -->
      <textarea
        id="prompt-input"
        ref="textareaEl"
        v-model="draft"
        class="block max-h-40 min-h-11 w-full resize-none bg-transparent px-3 pt-2.5 text-[13px] leading-relaxed outline-none read-only:text-muted-foreground placeholder:text-muted-foreground"
        :placeholder="
          streaming ? 'Waiting for generation to finish…' : 'Describe the app you want to build…'
        "
        aria-label="Message Genesis"
        :aria-describedby="describedBy"
        :aria-disabled="blocked || undefined"
        :readonly="streaming"
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
            id="composer-counter"
            class="font-mono text-[11px]"
            :class="overLimit ? 'text-destructive-soft' : 'text-warning'"
          >
            {{ draft.length.toLocaleString() }} / {{ MAX_CHARS.toLocaleString() }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span id="composer-hint" class="hidden text-[11px] text-muted-foreground xl:block">
            <span aria-hidden="true">⏎ Send · ⇧⏎ New line</span>
            <span class="sr-only">Press Enter to send. Press Shift plus Enter for a new line.</span>
          </span>
          <Button
            v-if="streaming"
            ref="stopButton"
            size="icon"
            variant="outline"
            class="size-8 border-destructive/50 text-destructive-soft hover:bg-destructive/10"
            aria-label="Stop generation"
            :aria-keyshortcuts="`${ariaMod}+Period`"
            @click="generation.cancel()"
          >
            <Square class="size-3.5" aria-hidden="true" />
          </Button>
          <Button
            v-else
            size="icon"
            class="size-8"
            :disabled="!canSend"
            :aria-disabled="!canSend || undefined"
            :aria-describedby="blocked ? 'composer-blocked-reason' : undefined"
            aria-label="Send message"
            :aria-keyshortcuts="`Enter ${ariaMod}+Enter`"
            @click="submit"
          >
            <ArrowUp class="size-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
