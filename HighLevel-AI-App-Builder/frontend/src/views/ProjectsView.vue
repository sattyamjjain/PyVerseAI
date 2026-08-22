<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  ArchiveRestore,
  FolderOpen,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import HlBanner from '@/components/hl/HlBanner.vue'
import HlConnectDialog from '@/components/hl/HlConnectDialog.vue'
import UserMenu from '@/components/workspace/UserMenu.vue'
import { relativeTime } from '@/lib/time'
import { useProjectsStore, type ProjectRow } from '@/stores/projects'

const router = useRouter()
const projects = useProjectsStore()

const tab = ref<'all' | 'trash'>('all')
const createOpen = ref(false)
const createName = ref('')
const createDescription = ref('')
const creating = ref(false)
const nameInput = ref<InstanceType<typeof Input> | null>(null)

const renameTarget = ref<ProjectRow | null>(null)
const renameDraft = ref('')
const trashTarget = ref<ProjectRow | null>(null)
const newProjectBtn = ref<InstanceType<typeof Button> | null>(null)

const list = computed(() => (tab.value === 'all' ? projects.active : projects.trashed))

onMounted(() => projects.subscribe())
onBeforeUnmount(() => projects.unsubscribe())

async function openCreate() {
  createName.value = ''
  createDescription.value = ''
  createOpen.value = true
  await nextTick()
  document.querySelector<HTMLInputElement>('#project-name')?.focus()
}

async function create() {
  const name = createName.value.trim()
  if (!name || creating.value) return
  creating.value = true
  try {
    const id = await projects.createProject(name, createDescription.value)
    createOpen.value = false
    await router.push({ name: 'workspace', params: { id } })
  } catch (err) {
    toast.error(err instanceof Error ? err.message : 'Could not create the project.')
  } finally {
    creating.value = false
  }
}

async function commitRename() {
  const target = renameTarget.value
  const name = renameDraft.value.trim()
  renameTarget.value = null
  if (!target || !name || name === target.name) return
  await projects.renameProject(target.id, name)
}

async function moveToTrash() {
  const target = trashTarget.value
  trashTarget.value = null
  if (!target) return
  await projects.setTrashed(target.id, true)
  // Focus-eviction: the card is gone; land on "New project".
  await nextTick()
  document.querySelector<HTMLElement>('#new-project-btn')?.focus()
  toast(`Moved “${target.name}” to trash`, {
    duration: 8000,
    action: { label: 'Undo', onClick: () => void projects.setTrashed(target.id, false) },
  })
}

async function restore(project: ProjectRow) {
  await projects.setTrashed(project.id, false)
  toast.success(`Restored “${project.name}”`)
}
</script>

<template>
  <div class="min-h-screen bg-background">
    <header class="border-b border-border" role="banner">
      <div class="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
        <div class="flex items-center gap-2">
          <div class="flex size-7 items-center justify-center rounded-lg bg-secondary" aria-hidden="true">
            <Sparkles class="size-4 text-primary" />
          </div>
          <span class="text-[15px] font-semibold">Genesis</span>
        </div>
        <UserMenu />
      </div>
    </header>

    <main id="main" class="mx-auto max-w-6xl px-4 py-8">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 tabindex="-1" class="text-xl font-semibold outline-none">Projects</h1>
          <p class="mt-0.5 text-[13px] text-muted-foreground">
            Each project is an app Genesis builds and refines with you.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <Tabs v-model="tab">
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="trash">
                Trash{{ projects.trashed.length ? ` (${projects.trashed.length})` : '' }}
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Button id="new-project-btn" ref="newProjectBtn" @click="openCreate">
            <Plus class="size-4" aria-hidden="true" /> New project
          </Button>
        </div>
      </div>

      <div class="mb-6">
        <HlBanner />
      </div>

      <!-- Loading skeletons -->
      <div v-if="projects.loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
        <Skeleton v-for="i in 6" :key="i" class="h-36 rounded-xl" />
      </div>

      <!-- Empty states -->
      <div
        v-else-if="list.length === 0"
        class="flex flex-col items-center gap-4 py-20 text-center"
      >
        <div class="flex size-[72px] items-center justify-center rounded-xl bg-secondary" aria-hidden="true">
          <component :is="tab === 'all' ? FolderOpen : Trash2" class="size-10 text-muted-foreground" />
        </div>
        <div>
          <p class="text-[15px] font-semibold">
            {{ tab === 'all' ? 'No projects yet' : 'Trash is empty' }}
          </p>
          <p class="mt-1 max-w-sm text-[13px] text-muted-foreground">
            {{
              tab === 'all'
                ? 'Describe an app and Genesis will build it into your HighLevel account.'
                : 'Projects you move to trash can be restored from here.'
            }}
          </p>
        </div>
        <Button v-if="tab === 'all'" @click="openCreate">
          <Plus class="size-4" aria-hidden="true" /> New project
        </Button>
      </div>

      <!-- Grid -->
      <ul v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <li v-for="project in list" :key="project.id">
          <Card class="group relative h-36 transition-colors hover:border-primary/40">
            <CardContent class="flex h-full flex-col p-4">
              <div class="flex items-start justify-between gap-2">
                <RouterLink
                  :to="{ name: 'workspace', params: { id: project.id } }"
                  class="min-w-0 flex-1 rounded-sm text-[14px] font-medium after:absolute after:inset-0 hover:underline"
                >
                  {{ project.name }}
                </RouterLink>
                <DropdownMenu>
                  <DropdownMenuTrigger as-child>
                    <button
                      type="button"
                      class="relative z-10 flex size-7 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:bg-accent hover:text-foreground focus-visible:opacity-100"
                      :aria-label="`Actions for ${project.name}`"
                    >
                      <MoreHorizontal class="size-4" aria-hidden="true" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <template v-if="tab === 'all'">
                      <DropdownMenuItem
                        @select="((renameTarget = project), (renameDraft = project.name))"
                      >
                        <Pencil class="size-4" aria-hidden="true" /> Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        class="text-destructive-soft"
                        @select="trashTarget = project"
                      >
                        <Trash2 class="size-4" aria-hidden="true" /> Move to trash
                      </DropdownMenuItem>
                    </template>
                    <DropdownMenuItem v-else @select="restore(project)">
                      <ArchiveRestore class="size-4" aria-hidden="true" /> Restore
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
              <p class="mt-1 line-clamp-2 flex-1 text-[13px] text-muted-foreground">
                {{ project.description || 'No description' }}
              </p>
              <p class="text-[11px] text-muted-foreground">
                Updated {{ relativeTime(project.updatedAt) }}
              </p>
            </CardContent>
          </Card>
        </li>
      </ul>
    </main>

    <!-- Create project -->
    <Dialog v-model:open="createOpen">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>Name it after the app you want Genesis to build.</DialogDescription>
        </DialogHeader>
        <form class="space-y-4" @submit.prevent="create">
          <div class="space-y-1.5">
            <Label for="project-name">Name</Label>
            <Input id="project-name" ref="nameInput" v-model="createName" required maxlength="120" />
          </div>
          <div class="space-y-1.5">
            <Label for="project-description">Description <span class="text-muted-foreground">(optional)</span></Label>
            <Textarea id="project-description" v-model="createDescription" rows="3" maxlength="2000" />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" @click="createOpen = false">Cancel</Button>
            <Button type="submit" :disabled="!createName.trim() || creating">
              <Loader2 v-if="creating" class="size-4 animate-spin" aria-hidden="true" />
              Create project
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- Rename -->
    <Dialog :open="renameTarget !== null" @update:open="(v) => !v && (renameTarget = null)">
      <DialogContent class="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Rename project</DialogTitle>
        </DialogHeader>
        <form class="space-y-4" @submit.prevent="commitRename">
          <div class="space-y-1.5">
            <Label for="rename-input">Name</Label>
            <Input id="rename-input" v-model="renameDraft" required maxlength="120" autofocus />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" @click="renameTarget = null">Cancel</Button>
            <Button type="submit" :disabled="!renameDraft.trim()">Rename</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- Move to trash confirm -->
    <AlertDialog :open="trashTarget !== null" @update:open="(v) => !v && (trashTarget = null)">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Move to trash?</AlertDialogTitle>
          <AlertDialogDescription>
            “{{ trashTarget?.name }}” will move to the trash. You can restore it any time.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            @click="moveToTrash"
          >
            Move to trash
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <HlConnectDialog />
  </div>
</template>
