<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, Loader2, Sparkles } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuthStore } from '@/stores/auth'
import { authErrorMessage } from '@/lib/authErrors'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const formError = ref('')
const emailInput = ref<InstanceType<typeof Input> | null>(null)

async function onSubmit() {
  formError.value = ''
  if (!email.value || !password.value) {
    formError.value = 'Enter your email and password.'
    focusFirstInvalid()
    return
  }
  submitting.value = true
  try {
    await authStore.signIn(email.value, password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    await router.replace(redirect ?? { name: 'projects' })
  } catch (err) {
    formError.value = authErrorMessage(err)
    focusFirstInvalid()
  } finally {
    submitting.value = false
  }
}

function focusFirstInvalid() {
  document.querySelector<HTMLInputElement>('#signin-email')?.focus()
}
</script>

<template>
  <main id="main" class="flex min-h-screen items-center justify-center bg-background p-4">
    <Card class="w-full max-w-sm">
      <CardHeader class="space-y-2 text-center">
        <div
          class="mx-auto flex size-12 items-center justify-center rounded-xl bg-secondary"
          aria-hidden="true"
        >
          <Sparkles class="size-6 text-primary" />
        </div>
        <CardTitle>
          <h1 tabindex="-1" class="text-2xl font-semibold outline-none">Sign in to Genesis</h1>
        </CardTitle>
        <CardDescription>Build HighLevel apps by describing them.</CardDescription>
      </CardHeader>
      <CardContent>
        <form novalidate class="space-y-4" @submit.prevent="onSubmit">
          <div
            v-if="formError"
            id="signin-error"
            class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-[13px] text-destructive-soft"
          >
            {{ formError }}
          </div>
          <div class="space-y-1.5">
            <Label for="signin-email">Email</Label>
            <Input
              id="signin-email"
              ref="emailInput"
              v-model="email"
              type="email"
              autocomplete="email"
              required
              :aria-invalid="!!formError || undefined"
              :aria-describedby="formError ? 'signin-error' : undefined"
            />
          </div>
          <div class="space-y-1.5">
            <Label for="signin-password">Password</Label>
            <div class="relative">
              <Input
                id="signin-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                class="pr-10"
                :aria-invalid="!!formError || undefined"
                :aria-describedby="formError ? 'signin-error' : undefined"
              />
              <button
                type="button"
                class="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
                :aria-pressed="showPassword"
                aria-label="Show password"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" class="size-4" aria-hidden="true" />
                <Eye v-else class="size-4" aria-hidden="true" />
              </button>
            </div>
          </div>
          <Button type="submit" class="w-full" :disabled="submitting">
            <Loader2 v-if="submitting" class="size-4 animate-spin" aria-hidden="true" />
            {{ submitting ? 'Signing in…' : 'Sign in' }}
          </Button>
        </form>
        <p class="mt-4 text-center text-[13px] text-muted-foreground">
          New here?
          <RouterLink to="/sign-up" class="font-medium text-foreground underline-offset-4 hover:underline">
            Create an account
          </RouterLink>
        </p>
      </CardContent>
    </Card>
  </main>
</template>
