<script setup lang="ts">
import { ref } from 'vue'
import { FileCode2 } from 'lucide-vue-next'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import FileTree from '@/components/editor/FileTree.vue'
import EditorTabs from '@/components/editor/EditorTabs.vue'
import CodeEditor from '@/components/editor/CodeEditor.vue'
import EditorStatusStrip from '@/components/editor/EditorStatusStrip.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const emit = defineEmits<{ cycle: [dir: 1 | -1] }>()

const workspace = useWorkspaceStore()

const treeVisible = ref(true)
const cursorLine = ref(1)
const cursorCol = ref(1)
const editorRef = ref<InstanceType<typeof CodeEditor> | null>(null)

function onCursor(line: number, col: number) {
  cursorLine.value = line
  cursorCol.value = col
}

defineExpose({
  focusEditor: () => editorRef.value?.focus(),
})
</script>

<template>
  <!-- The labeled landmark is the region wrapper in WorkspaceView. -->
  <div class="flex h-full min-h-0 flex-col">
    <h2 class="sr-only">Code editor</h2>
    <EditorTabs :tree-visible="treeVisible" @toggle-tree="treeVisible = !treeVisible" />
    <div class="min-h-0 flex-1">
      <ResizablePanelGroup direction="horizontal" auto-save-id="genesis-editor-split">
        <ResizablePanel
          v-if="treeVisible"
          :default-size="24"
          :min-size="14"
          :max-size="40"
          class="bg-background"
        >
          <FileTree />
        </ResizablePanel>
        <ResizableHandle v-if="treeVisible" aria-label="Resize file tree" />
        <ResizablePanel :default-size="76">
          <div v-if="workspace.filePaths.length === 0" class="flex h-full flex-col items-center justify-center gap-3 bg-editor text-center">
            <FileCode2 class="size-10 text-muted-foreground/50" aria-hidden="true" />
            <p class="max-w-56 text-[13px] text-muted-foreground">
              Generated code appears here. Describe your app in the chat to get started.
            </p>
          </div>
          <div v-else-if="workspace.activePath === null" class="flex h-full items-center justify-center bg-editor">
            <p class="text-[13px] text-muted-foreground">Select a file to view it.</p>
          </div>
          <CodeEditor v-show="workspace.activePath !== null" ref="editorRef" @cursor="onCursor" @cycle="emit('cycle', $event)" />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
    <EditorStatusStrip :line="cursorLine" :col="cursorCol" />
  </div>
</template>
