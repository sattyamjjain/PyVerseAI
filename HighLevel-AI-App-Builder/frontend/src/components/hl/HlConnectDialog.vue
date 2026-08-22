<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Database, Loader2, Plug, Unplug, Zap } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { connectHighLevel } from '@/lib/oauth'
import { callFn } from '@/lib/api'
import { announce } from '@/composables/useAnnouncer'

const auth = useAuthStore()
const ui = useUiStore()

const connecting = ref(false)
const disconnecting = ref(false)
const seeding = ref(false)
const confirmDisconnect = ref(false)
const errorText = ref('')

const connected = computed(() => auth.hlConnected)

async function connect() {
  errorText.value = ''
  connecting.value = true
  try {
    const result = await connectHighLevel()
    if (result.ok) {
      toast.success('HighLevel connected')
      announce('HighLevel connected')
    } else if (result.reason) {
      errorText.value = result.reason
    }
  } catch (err) {
    errorText.value = err instanceof Error ? err.message : 'Connection failed.'
  } finally {
    connecting.value = false
  }
}

async function disconnect() {
  disconnecting.value = true
  try {
    await callFn('hlDisconnect', {})
    toast('HighLevel disconnected')
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Disconnect failed.')
  } finally {
    disconnecting.value = false
    confirmDisconnect.value = false
  }
}

async function seed() {
  seeding.value = true
  try {
    const res = await callFn<{
      seeded: { contacts: number; conversations: number; appointments: number }
      notes?: string[]
    }>('seedSandbox', {})
    toast.success(
      `Seeded ${res.seeded.contacts} contacts, ${res.seeded.conversations} conversations, ${res.seeded.appointments} appointments`,
    )
    for (const note of res.notes ?? []) toast(note)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Seeding failed.')
  } finally {
    seeding.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="ui.hlDialogOpen">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Zap class="size-4 text-primary" aria-hidden="true" />
          HighLevel connection
        </DialogTitle>
        <DialogDescription>
          Genesis generates apps that read live CRM data from one connected HighLevel location.
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4">
        <div class="flex items-center justify-between rounded-lg border border-border bg-card p-3">
          <div class="min-w-0">
            <p class="text-[13px] font-medium">
              {{ connected ? auth.hl?.locationName || 'Connected location' : 'Not connected' }}
            </p>
            <p class="truncate text-xs text-muted-foreground">
              {{
                connected
                  ? `Location ${auth.hl?.locationId}`
                  : auth.hl?.status === 'needs_reconnect'
                    ? 'Your connection expired — reconnect to continue.'
                    : 'Connect a sandbox location to start generating.'
              }}
            </p>
          </div>
          <Badge
            :class="
              connected
                ? 'border-success/40 bg-success/10 text-success'
                : 'border-border bg-secondary text-muted-foreground'
            "
            variant="outline"
          >
            {{ connected ? 'Connected' : auth.hl?.status === 'needs_reconnect' ? 'Expired' : 'Off' }}
          </Badge>
        </div>

        <p
          v-if="errorText"
          class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive-soft"
        >
          {{ errorText }}
        </p>

        <div v-if="connected" class="rounded-lg border border-border p-3">
          <p class="text-[13px] font-medium">Demo data</p>
          <p class="mb-2 text-xs text-muted-foreground">
            Fill the sandbox with sample contacts, conversations, and appointments (takes ~20s).
          </p>
          <Button size="sm" variant="secondary" :disabled="seeding" @click="seed">
            <Loader2 v-if="seeding" class="size-4 animate-spin" aria-hidden="true" />
            <Database v-else class="size-4" aria-hidden="true" />
            {{ seeding ? 'Seeding…' : 'Seed demo data' }}
          </Button>
        </div>
      </div>

      <DialogFooter class="gap-2 sm:justify-between">
        <Button
          v-if="connected"
          variant="ghost"
          class="text-destructive-soft hover:text-destructive-soft"
          :disabled="disconnecting"
          @click="confirmDisconnect = true"
        >
          <Unplug class="size-4" aria-hidden="true" />
          Disconnect
        </Button>
        <Button :disabled="connecting" @click="connect">
          <Loader2 v-if="connecting" class="size-4 animate-spin" aria-hidden="true" />
          <Plug v-else class="size-4" aria-hidden="true" />
          {{ connected ? 'Reconnect' : connecting ? 'Waiting for HighLevel…' : 'Connect HighLevel' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>

  <AlertDialog v-model:open="confirmDisconnect">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Disconnect HighLevel?</AlertDialogTitle>
        <AlertDialogDescription>
          Generated apps will stop receiving CRM data until you reconnect. Your projects and code
          stay untouched.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>Cancel</AlertDialogCancel>
        <AlertDialogAction
          class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          @click="disconnect"
        >
          Disconnect
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
