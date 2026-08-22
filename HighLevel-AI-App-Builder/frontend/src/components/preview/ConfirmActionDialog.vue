<script setup lang="ts">
import { computed } from 'vue'
import { ShieldAlert } from 'lucide-vue-next'
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
import { useUiStore } from '@/stores/ui'

/**
 * The unspoofable write gate: generated code has zero network access, so every
 * HighLevel WRITE necessarily transits this parent-rendered dialog first.
 */
const ui = useUiStore()

const current = computed(() => ui.confirmQueue[0] ?? null)
const open = computed(() => current.value !== null)
</script>

<template>
  <AlertDialog :open="open">
    <AlertDialogContent v-if="current">
      <AlertDialogHeader>
        <AlertDialogTitle class="flex items-center gap-2">
          <ShieldAlert class="size-4 text-warning" aria-hidden="true" />
          Allow this action?
        </AlertDialogTitle>
        <AlertDialogDescription>
          The generated app wants to <strong>{{ current.info.label.toLowerCase() }}</strong> in your
          HighLevel account.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <pre
        class="max-h-40 overflow-auto rounded-md border border-border bg-editor px-3 py-2 font-mono text-xs text-muted-foreground"
        >{{ current.info.detail }}</pre
      >
      <AlertDialogFooter>
        <AlertDialogCancel @click="ui.settleConfirm(false)">Deny</AlertDialogCancel>
        <AlertDialogAction @click="ui.settleConfirm(true)">Allow</AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
