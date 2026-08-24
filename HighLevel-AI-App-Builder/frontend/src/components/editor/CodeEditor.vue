<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDebounceFn, useThrottleFn } from '@vueuse/core'
import { monaco } from '@/lib/monaco'
import { getOrCreateModel } from '@/lib/models'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { useUiStore } from '@/stores/ui'

const emit = defineEmits<{ cycle: [dir: 1 | -1]; cursor: [line: number, col: number] }>()

const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const ui = useUiStore()

const containerEl = ref<HTMLElement | null>(null)
let editor: ReturnType<typeof monaco.editor.create> | null = null

const prm = window.matchMedia('(prefers-reduced-motion: reduce)')

const debouncedSave = useDebounceFn((path: string) => {
  void workspace.saveFile(path)
}, 800)

const throttledReveal = useThrottleFn((line: number) => {
  editor?.revealLine(line)
}, 100)

function baseOptions(): Parameters<typeof monaco.editor.create>[1] {
  return {
    theme: 'genesis-dark',
    fontFamily: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
    fontSize: 13,
    lineHeight: 21,
    fontLigatures: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    padding: { top: 12 },
    automaticLayout: true,
    folding: true,
    renderLineHighlight: 'line',
    scrollbar: { verticalScrollbarSize: 10, horizontalScrollbarSize: 10 },
    accessibilitySupport: ui.srOptimized ? 'on' : 'auto',
    accessibilityPageSize: 100,
    readOnlyMessage: { value: 'Read-only while Genesis is generating' },
    cursorBlinking: prm.matches ? 'solid' : 'blink',
    cursorSmoothCaretAnimation: prm.matches ? 'off' : 'on',
    smoothScrolling: !prm.matches,
    tabSize: 2,
  }
}

onMounted(() => {
  if (!containerEl.value) return
  editor = monaco.editor.create(containerEl.value, { ...baseOptions(), model: null })

  // A11y item 16: Cmd/Ctrl+S and F6/Shift+F6 must work INSIDE Monaco.
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    if (workspace.activePath) {
      void workspace.saveFile(workspace.activePath, { announceResult: true })
    }
  })
  editor.addCommand(monaco.KeyCode.F6, () => emit('cycle', 1))
  editor.addCommand(monaco.KeyMod.Shift | monaco.KeyCode.F6, () => emit('cycle', -1))

  editor.onDidChangeCursorPosition((e) => emit('cursor', e.position.lineNumber, e.position.column))

  editor.onDidChangeModelContent(() => {
    const path = workspace.activePath
    if (!path || generation.isActive) return
    workspace.markDirty(path)
    void debouncedSave(path)
  })

  syncModel()
  syncReadOnly()
})

onBeforeUnmount(() => {
  editor?.dispose()
  editor = null
})

function syncModel() {
  if (!editor) return
  const path = workspace.activePath
  if (!path) {
    editor.setModel(null)
    return
  }
  const row = workspace.files.get(path)
  const model = getOrCreateModel(path, row?.content ?? '')
  if (editor.getModel() !== model) {
    editor.setModel(model)
    editor.updateOptions({ ariaLabel: `${path}, code editor` })
  }
}

function syncReadOnly() {
  editor?.updateOptions({ readOnly: generation.isActive })
}

watch(() => workspace.activePath, syncModel)
watch(() => generation.isActive, syncReadOnly)
watch(
  () => ui.srOptimized,
  (on) => editor?.updateOptions({ accessibilitySupport: on ? 'on' : 'auto' }),
)

// Follow the stream: open the streaming file and keep the tail in view.
watch(
  () => generation.streamingPath,
  (path) => {
    if (path && ui.followMode) workspace.openFile(path)
  },
)
watch(
  () => generation.followTick,
  () => {
    if (!ui.followMode || !editor) return
    const path = generation.streamingPath
    if (!path || workspace.activePath !== path) return
    const model = editor.getModel()
    if (model) void throttledReveal(model.getLineCount())
  },
)

defineExpose({
  focus: () => editor?.focus(),
})
</script>

<template>
  <div ref="containerEl" class="h-full min-h-0 w-full bg-editor" />
</template>
