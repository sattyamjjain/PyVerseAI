<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, EyeOff, Loader2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import AuthShell from '@/components/auth/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'
import { authErrorMessage } from '@/lib/authErrors'

const router = useRouter()
const authStore = useAuthStore()

const displayName = ref('')
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const formError = ref('')

async function onSubmit() {
  formError.value = ''
  if (!displayName.value.trim()) {
    formError.value = 'Enter your name.'
    document.querySelector<HTMLInputElement>('#signup-name')?.focus()
    return
  }
  if (!email.value || password.value.length < 6) {
    formError.value = 'Enter a valid email and a password of at least 6 characters.'
    document.querySelector<HTMLInputElement>('#signup-email')?.focus()
    return
  }
  submitting.value = true
  try {
    await authStore.signUp(email.value, password.value, displayName.value.trim())
    await router.replace({ name: 'projects' })
  } catch (err) {
    formError.value = authErrorMessage(err)
    document.querySelector<HTMLInputElement>('#signup-email')?.focus()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthShell>
    <h1 tabindex="-1" class="text-2xl font-semibold tracking-tight outline-none">
      Create your account
    </h1>
    <p class="mt-1.5 text-[13px] text-muted-foreground">
      Genesis builds HighLevel apps from plain English.
    </p>

    <form novalidate class="mt-8 space-y-4" @submit.prevent="onSubmit">
      <div
        v-if="formError"
        id="signup-error"
        class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive-soft"
      >
        {{ formError }}
      </div>
      <div class="space-y-1.5">
        <Label for="signup-name">Name</Label>
        <Input
          id="signup-name"
          v-model="displayName"
          type="text"
          autocomplete="name"
          required
          class="h-10"
          :aria-invalid="!!formError || undefined"
          :aria-describedby="formError ? 'signup-error' : undefined"
        />
      </div>
      <div class="space-y-1.5">
        <Label for="signup-email">Email</Label>
        <Input
          id="signup-email"
          v-model="email"
          type="email"
          autocomplete="email"
          required
          class="h-10"
          :aria-invalid="!!formError || undefined"
          :aria-describedby="formError ? 'signup-error' : undefined"
        />
      </div>
      <div class="space-y-1.5">
        <Label for="signup-password">Password</Label>
        <div class="relative">
          <Input
            id="signup-password"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="new-password"
            required
            minlength="6"
            class="h-10 pr-10"
            aria-describedby="signup-password-hint"
            :aria-invalid="!!formError || undefined"
          />
          <button
            type="button"
            class="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground transition-colors duration-150 hover:text-foreground"
            :aria-pressed="showPassword"
            aria-label="Show password"
            @click="showPassword = !showPassword"
          >
            <EyeOff v-if="showPassword" class="size-4" aria-hidden="true" />
            <Eye v-else class="size-4" aria-hidden="true" />
          </button>
        </div>
        <p id="signup-password-hint" class="text-xs text-muted-foreground">
          At least 6 characters.
        </p>
      </div>
      <Button type="submit" class="h-10 w-full" :disabled="submitting">
        <Loader2 v-if="submitting" class="size-4 animate-spin" aria-hidden="true" />
        {{ submitting ? 'Creating account…' : 'Create account' }}
      </Button>
    </form>
    <p class="mt-6 text-[13px] text-muted-foreground">
      Already have an account?
      <RouterLink
        to="/sign-in"
        class="font-medium text-foreground underline-offset-4 hover:underline"
      >
        Sign in
      </RouterLink>
    </p>
  </AuthShell>
</template>
