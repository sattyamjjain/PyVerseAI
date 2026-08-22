<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Camera, GitCompare, MoreHorizontal, RotateCcw } from 'lucide-vue-next'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { absoluteTime, relativeTime } from '@/lib/time'
import { callFn } from '@/lib/api'
import { useWorkspaceStore, type SnapshotRow } from '@/stores/workspace'
import { useUiStore } from '@/stores/ui'

const workspace = useWorkspaceStore()
const ui = useUiStore()

const restoreTarget = ref<SnapshotRow | null>(null)
/** Survives the dialog's own close handler: reka closes (and we null
 *  restoreTarget) BEFORE our Action @click runs, so the click consumes this. */
let pendingRestoreId: string | null = null

function beginRestore(snapshot: SnapshotRow) {
  pendingRestoreId = snapshot.id
  restoreTarget.value = snapshot
}

function confirmRestore() {
  if (restoring.value || !pendingRestoreId) return
  const id = pendingRestoreId
  pendingRestoreId = null
  void restore(id)
}
const restoring = ref(false)

const kindLabel: Record<string, string> = {
  backup: 'Backup',
  restore: 'Restored',
  stopped: 'Stopped early',
}

async function restore(snapshotId: string, isUndo = false) {
  const projectId = workspace.projectId
  if (!projectId) return
  restoring.value = true
  ui.restoring = true
  ui.snapshotSheetOpen = false
  try {
    const res = await callFn<{ backupSnapshotId: string }>('restoreSnapshot', {
      projectId,
      snapshotId,
    })
    // Toast is the visual channel; sonner's own live region covers SR users.
    if (!isUndo) {
      toast.success('Snapshot restored', {
        duration: 8000,
        action: {
          label: 'Undo',
          onClick: () => void restore(res.backupSnapshotId, true),
        },
      })
    } else {
      toast.success('Restore undone')
    }
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Restore failed')
  } finally {
    restoring.value = false
    ui.restoring = false
    restoreTarget.value = null
    // Focus-eviction: the sheet closed programmatically — land on its trigger.
    await nextTick()
    document.querySelector<HTMLElement>('#snapshot-history-btn')?.focus()
  }
}

defineExpose({ restoring })
</script>

<template>
  <Sheet v-model:open="ui.snapshotSheetOpen">
    <SheetContent side="right" class="w-full gap-0 sm:max-w-md">
      <SheetHeader class="border-b border-border">
        <SheetTitle class="flex items-center gap-2">
          <Camera class="size-4" aria-hidden="true" /> Snapshots
        </SheetTitle>
        <SheetDescription>
          {{ workspace.snapshots.length }}
          {{ workspace.snapshots.length === 1 ? 'version' : 'versions' }} — every generation and
          restore is saved automatically.
        </SheetDescription>
      </SheetHeader>
      <ScrollArea class="min-h-0 flex-1">
        <p v-if="workspace.snapshots.length === 0" class="px-4 py-6 text-[13px] text-muted-foreground">
          No snapshots yet — they appear after your first generation.
        </p>
        <ul v-else class="divide-y divide-border">
          <li
            v-for="(snapshot, index) in workspace.snapshots"
            :key="snapshot.id"
            class="group flex items-start gap-3 px-4 py-3"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <Tooltip>
                  <TooltipTrigger as-child>
                    <span tabindex="0" class="rounded-sm text-[13px] font-medium">
                      {{ relativeTime(snapshot.createdAt) }}
                      <span class="sr-only">, {{ absoluteTime(snapshot.createdAt) }}</span>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>{{ absoluteTime(snapshot.createdAt) }}</TooltipContent>
                </Tooltip>
                <Badge v-if="index === 0" variant="outline" class="border-primary/50 text-primary">
                  Current
                </Badge>
                <Badge
                  v-else-if="kindLabel[snapshot.kind]"
                  variant="outline"
                  class="text-muted-foreground"
                >
                  {{ kindLabel[snapshot.kind] }}
                </Badge>
              </div>
              <p v-if="snapshot.promptExcerpt" class="mt-1 line-clamp-2 text-xs text-muted-foreground">
                “{{ snapshot.promptExcerpt }}”
              </p>
              <p class="mt-1 font-mono text-[11px] text-muted-foreground">
                {{ snapshot.fileCount }} {{ snapshot.fileCount === 1 ? 'file' : 'files' }}
                <template v-if="snapshot.added + snapshot.removed > 0">
                  · <span class="text-success">+{{ snapshot.added }}</span>
                  <span class="text-destructive-soft"> −{{ snapshot.removed }}</span>
                </template>
              </p>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <button
                  type="button"
                  class="flex size-7 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-accent hover:text-foreground focus-visible:opacity-100"
                  :aria-label="`Snapshot actions for ${relativeTime(snapshot.createdAt)}`"
                >
                  <MoreHorizontal class="size-4" aria-hidden="true" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem :disabled="index === 0" @select="beginRestore(snapshot)">
                  <RotateCcw class="size-4" aria-hidden="true" /> Restore
                </DropdownMenuItem>
                <DropdownMenuItem
                  @select="
                    ui.openDiff(snapshot.id, 'current', `Snapshot ${relativeTime(snapshot.createdAt)} → Current`)
                  "
                >
                  <GitCompare class="size-4" aria-hidden="true" /> Compare with current
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </li>
        </ul>
      </ScrollArea>
    </SheetContent>
  </Sheet>

  <AlertDialog :open="restoreTarget !== null" @update:open="(v) => !v && (restoreTarget = null)">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Restore this snapshot?</AlertDialogTitle>
        <AlertDialogDescription>
          This will replace the current files — a backup snapshot will be created first, so nothing
          is lost.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel :aria-disabled="restoring || undefined" :class="restoring ? 'opacity-40' : ''">
          Cancel
        </AlertDialogCancel>
        <AlertDialogAction
          :aria-disabled="restoring || undefined"
          :class="restoring ? 'opacity-40' : ''"
          @click="confirmRestore()"
        >
          Restore
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
