<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Keyboard, LogOut, MonitorSpeaker, Plug } from 'lucide-vue-next'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const props = defineProps<{ showShortcuts?: boolean }>()

const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const initials = computed(() => {
  const name = auth.profile?.displayName || auth.user?.email || '?'
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

async function signOut() {
  await auth.signOutUser()
  await router.replace({ name: 'sign-in' })
}
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <button
        type="button"
        class="rounded-full outline-none transition-opacity hover:opacity-90"
        aria-label="Account menu"
      >
        <Avatar class="size-7 text-[11px]">
          <AvatarFallback class="bg-secondary font-medium">{{ initials }}</AvatarFallback>
        </Avatar>
      </button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-60">
      <DropdownMenuLabel class="flex flex-col">
        <span class="truncate text-[13px]">{{ auth.profile?.displayName || 'Account' }}</span>
        <span class="truncate text-xs font-normal text-muted-foreground">{{
          auth.user?.email
        }}</span>
      </DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuItem @select="ui.hlDialogOpen = true">
        <Plug class="size-4" aria-hidden="true" />
        HighLevel connection
      </DropdownMenuItem>
      <DropdownMenuItem v-if="props.showShortcuts" @select="ui.shortcutsOpen = true">
        <Keyboard class="size-4" aria-hidden="true" />
        Keyboard shortcuts
      </DropdownMenuItem>
      <DropdownMenuCheckboxItem
        :model-value="ui.srOptimized"
        @update:model-value="ui.setSrOptimized($event === true)"
      >
        <MonitorSpeaker class="size-4" aria-hidden="true" />
        Screen reader optimized editor
      </DropdownMenuCheckboxItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem @select="signOut">
        <LogOut class="size-4" aria-hidden="true" />
        Sign out
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
