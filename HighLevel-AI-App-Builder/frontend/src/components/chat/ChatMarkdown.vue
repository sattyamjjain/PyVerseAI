<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useThrottleFn } from '@vueuse/core'
import { toast } from 'vue-sonner'
import { renderMarkdown } from '@/lib/markdown'

const props = defineProps<{ source: string; streaming?: boolean }>()

// While streaming, re-render at most every ~80ms; when static, render eagerly.
// A re-render replaces the v-html subtree — if focus is inside (a code-copy
// button), defer until focus leaves so we never destroy the focused element.
const html = ref(renderMarkdown(props.source))
const containerEl = ref<HTMLElement | null>(null)
let deferredWhileFocused = false

function renderNow() {
  if (containerEl.value?.contains(document.activeElement)) {
    deferredWhileFocused = true
    return
  }
  deferredWhileFocused = false
  html.value = renderMarkdown(props.source)
}

const applyRender = useThrottleFn(renderNow, 80, true)

function onFocusOut() {
  // Wait a tick so activeElement reflects the new focus target.
  setTimeout(() => {
    if (deferredWhileFocused) renderNow()
  }, 0)
}

watch(
  () => props.source,
  () => {
    if (props.streaming) void applyRender()
    else renderNow()
  },
)
watch(
  () => props.streaming,
  (s) => {
    if (!s) renderNow()
  },
)

const busy = computed(() => (props.streaming ? 'true' : undefined))

async function onClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.classList.contains('code-copy')) return
  const code = target.closest('.code-block')?.querySelector('code')?.textContent ?? ''
  try {
    await navigator.clipboard.writeText(code)
    toast('Copied to clipboard')
  } catch {
    toast.error('Copy failed')
  }
}
</script>

<template>
  <!-- The app's single v-html sink: markdown-it html:false + DOMPurify. -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div
    ref="containerEl"
    class="chat-prose"
    :aria-busy="busy"
    @click="onClick"
    @focusout="onFocusOut"
    v-html="html"
  />
</template>

<style>
.chat-prose {
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: break-word;
}
.chat-prose > * + * {
  margin-top: 0.6em;
}
.chat-prose h1,
.chat-prose h2,
.chat-prose h3,
.chat-prose h4 {
  font-weight: 600;
  line-height: 1.3;
}
.chat-prose h1 {
  font-size: 15px;
}
.chat-prose h2 {
  font-size: 14px;
}
.chat-prose h3,
.chat-prose h4 {
  font-size: 13px;
}
.chat-prose ul,
.chat-prose ol {
  padding-left: 20px;
}
.chat-prose ul {
  list-style: disc;
}
.chat-prose ol {
  list-style: decimal;
}
.chat-prose li + li {
  margin-top: 0.25em;
}
.chat-prose a {
  color: var(--info);
  text-decoration: underline; /* WCAG 1.4.1 — never color alone */
  text-underline-offset: 2px;
}
.chat-prose a:hover {
  text-decoration-thickness: 2px;
}
.chat-prose code:not(pre code) {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--secondary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 4px;
}
.chat-prose .code-block {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--editor);
  overflow: hidden;
}
.chat-prose .code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 28px;
  padding: 0 10px;
  border-bottom: 1px solid var(--border);
  color: var(--muted-foreground);
  font-family: var(--font-mono);
  font-size: 11px;
}
.chat-prose .code-copy {
  font-family: var(--font-sans);
  font-size: 11px;
  color: var(--muted-foreground);
  padding: 2px 6px;
  border-radius: 4px;
}
.chat-prose .code-copy:hover {
  background: var(--accent);
  color: var(--foreground);
}
.chat-prose pre {
  margin: 0;
  padding: 10px 12px;
  overflow-x: auto;
  max-height: 320px;
  overflow-y: auto;
}
.chat-prose pre code {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 19px;
  white-space: pre;
}
/* highlight.js token colors tuned for the dark editor surface */
.chat-prose .hljs-keyword {
  color: #7aa2f7;
}
.chat-prose .hljs-string {
  color: #95d3a2;
}
.chat-prose .hljs-number,
.chat-prose .hljs-literal {
  color: #fbbf24;
}
.chat-prose .hljs-comment {
  color: #7d8798; /* ≥4.5:1 on the #14171d code surface */
  font-style: italic;
}
.chat-prose .hljs-title,
.chat-prose .hljs-function {
  color: #5fb4f0;
}
.chat-prose .hljs-tag,
.chat-prose .hljs-name {
  color: #f7768e;
}
.chat-prose .hljs-attr {
  color: #e5c07b;
}
</style>
