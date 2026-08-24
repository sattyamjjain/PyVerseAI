<script setup lang="ts">
import { computed } from 'vue'
import { TreeItem, TreeRoot } from 'reka-ui'
import {
  Check,
  ChevronRight,
  FileCode2,
  FileJson,
  FileText,
  Folder,
  FolderOpen,
} from 'lucide-vue-next'
import { useWorkspaceStore } from '@/stores/workspace'
import { useGenerationStore } from '@/stores/generation'
import { useUiStore } from '@/stores/ui'

interface TreeNode {
  name: string
  path: string
  isFile: boolean
  children?: TreeNode[]
}

const workspace = useWorkspaceStore()
const generation = useGenerationStore()
const ui = useUiStore()

const tree = computed<TreeNode[]>(() => {
  const root: TreeNode[] = []
  for (const path of workspace.filePaths) {
    const segments = path.split('/')
    let level = root
    let prefix = ''
    for (let i = 0; i < segments.length; i++) {
      const name = segments[i]!
      prefix = prefix ? `${prefix}/${name}` : name
      const isFile = i === segments.length - 1
      let node = level.find((n) => n.name === name && n.isFile === isFile)
      if (!node) {
        node = { name, path: prefix, isFile, children: isFile ? undefined : [] }
        level.push(node)
      }
      if (!isFile) level = node.children!
    }
  }
  const sort = (nodes: TreeNode[]) => {
    nodes.sort((a, b) =>
      a.isFile === b.isFile ? a.name.localeCompare(b.name) : a.isFile ? 1 : -1,
    )
    nodes.forEach((n) => n.children && sort(n.children))
  }
  sort(root)
  return root
})

/** Bind reka's selection to the active file so aria-selected is exposed. */
const selectedNode = computed<TreeNode | undefined>(() => {
  if (!workspace.activePath) return undefined
  const find = (nodes: TreeNode[]): TreeNode | undefined => {
    for (const n of nodes) {
      if (n.isFile && n.path === workspace.activePath) return n
      if (n.children) {
        const hit = find(n.children)
        if (hit) return hit
      }
    }
    return undefined
  }
  return find(tree.value)
})

function iconFor(node: TreeNode) {
  if (!node.isFile) return Folder
  if (node.name.endsWith('.json')) return FileJson
  if (node.name.endsWith('.html') || node.name.endsWith('.css') || node.name.endsWith('.js'))
    return FileCode2
  return FileText
}

const fileState = computed(() => {
  const map = new Map<string, 'writing' | 'done' | 'new'>()
  for (const f of generation.liveFiles) {
    if (f.status === 'writing') map.set(f.path, 'writing')
    else map.set(f.path, f.action === 'create' && generation.isActive ? 'new' : 'done')
  }
  return map
})

function onSelect(node: TreeNode) {
  if (!node.isFile) return
  workspace.openFile(node.path)
  // Manual navigation mid-stream disarms follow mode.
  if (generation.isActive) ui.followMode = false
}
</script>

<template>
  <div class="h-full overflow-y-auto py-1.5">
    <p v-if="tree.length === 0" class="px-3 py-2 text-xs text-muted-foreground">No files yet.</p>
    <TreeRoot
      v-else
      v-slot="{ flattenItems }"
      :items="tree"
      :get-key="(item: TreeNode) => item.path + (item.isFile ? '' : '/')"
      :get-children="(item: TreeNode) => item.children"
      :default-expanded="tree.filter((n) => !n.isFile).map((n) => n.path + '/')"
      :model-value="selectedNode"
      class="select-none"
      aria-label="Project files"
    >
      <TreeItem
        v-for="item in flattenItems"
        v-slot="{ isExpanded }"
        :key="item._id"
        v-bind="item.bind"
        class="group flex h-7 w-full cursor-pointer items-center gap-1.5 px-2 font-mono text-xs outline-none hover:bg-accent focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring data-[selected]:bg-secondary"
        :class="{
          'border-l-2 border-primary pl-[6px]':
            item.value.isFile && workspace.activePath === item.value.path,
        }"
        :style="{ paddingLeft: `${8 + (item.level - 1) * 12}px` }"
        @select="onSelect(item.value)"
      >
        <ChevronRight
          v-if="!item.value.isFile"
          class="size-3.5 shrink-0 text-muted-foreground transition-transform duration-120"
          :class="{ 'rotate-90': isExpanded }"
          aria-hidden="true"
        />
        <component
          :is="!item.value.isFile && isExpanded ? FolderOpen : iconFor(item.value)"
          class="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
        <span class="min-w-0 flex-1 truncate">{{ item.value.name }}</span>
        <!-- Streaming state is part of the item's accessible name, not icon-only. -->
        <span v-if="fileState.get(item.value.path) === 'writing'" class="sr-only">, writing</span>
        <span v-else-if="fileState.get(item.value.path) === 'new'" class="sr-only">, new file</span>
        <span
          v-else-if="fileState.get(item.value.path) === 'done' && generation.isActive"
          class="sr-only"
          >, completed</span
        >
        <span
          v-if="fileState.get(item.value.path) === 'writing'"
          class="genesis-activity-dot size-1.5 shrink-0 rounded-full bg-primary"
          aria-hidden="true"
        />
        <span
          v-else-if="fileState.get(item.value.path) === 'new'"
          class="rounded bg-success/15 px-1 text-[10px] font-medium text-success"
          aria-hidden="true"
          >A</span
        >
        <Check
          v-else-if="fileState.get(item.value.path) === 'done' && generation.isActive"
          class="size-3 shrink-0 text-success"
          aria-hidden="true"
        />
      </TreeItem>
    </TreeRoot>
  </div>
</template>
