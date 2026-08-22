<script setup lang="ts">
import { FileQuestion } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
</script>

<template>
  <main id="main" class="flex min-h-screen items-center justify-center bg-background p-4">
    <Card class="w-full max-w-sm">
      <CardContent class="flex flex-col items-center gap-4 py-10 text-center">
        <div
          class="flex size-[72px] items-center justify-center rounded-xl bg-secondary"
          aria-hidden="true"
        >
          <FileQuestion class="size-10 text-muted-foreground" />
        </div>
        <h1 tabindex="-1" class="text-xl font-semibold outline-none">Page not found</h1>
        <p class="text-[13px] text-muted-foreground">
          The page you're looking for doesn't exist or was moved.
        </p>
        <Button as-child>
          <RouterLink to="/projects">Back to projects</RouterLink>
        </Button>
      </CardContent>
    </Card>
  </main>
</template>
