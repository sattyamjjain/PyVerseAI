<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
</script>

<template>
  <main id="main" class="min-h-screen bg-background lg:grid lg:grid-cols-[45fr_55fr]">
    <!-- Brand panel (decorative; the form column carries the semantics) -->
    <aside
      class="relative hidden overflow-hidden border-r border-border bg-editor p-10 lg:flex lg:flex-col"
      aria-hidden="true"
    >
      <div
        class="pointer-events-none absolute -top-40 -left-40 size-[480px] rounded-full opacity-[0.07]"
        style="background: radial-gradient(circle, oklch(0.83 0.19 84) 0%, transparent 70%)"
      />
      <div class="flex items-center gap-2.5">
        <div class="flex size-8 items-center justify-center rounded-lg bg-secondary">
          <Sparkles class="size-4.5 text-primary" />
        </div>
        <span class="text-[15px] font-semibold tracking-tight">Genesis</span>
      </div>
      <div class="mt-24 max-w-sm">
        <p class="text-2xl leading-snug font-semibold tracking-tight">
          Plain English in.<br />Working HighLevel apps out.
        </p>
        <p class="mt-3 text-[13px] leading-relaxed text-muted-foreground">
          Chat, code, and a live preview running on your real CRM data.
        </p>
      </div>
      <div class="pointer-events-none absolute right-0 -bottom-10 left-10 opacity-35">
        <img
          :src="'/screenshots/workspace.png'"
          alt=""
          class="w-full rounded-tl-xl border-t border-l border-border [mask-image:linear-gradient(to_bottom,black_20%,transparent_95%)]"
          onerror="this.style.display='none'"
        />
      </div>
    </aside>

    <!-- Form column -->
    <div class="flex min-h-screen items-center justify-center p-6 lg:min-h-0">
      <div class="w-full max-w-sm">
        <div class="mb-8 flex size-11 items-center justify-center rounded-xl bg-secondary lg:hidden" aria-hidden="true">
          <Sparkles class="size-5 text-primary" />
        </div>
        <slot />
      </div>
    </div>
  </main>
</template>
