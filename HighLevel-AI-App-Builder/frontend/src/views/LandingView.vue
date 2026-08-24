<script setup lang="ts">
import { CircleStop, Github, History, ShieldCheck, Sparkles } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import LandingShot from '@/components/landing/LandingShot.vue'

const steps = [
  {
    title: 'Describe',
    line: 'Say what you want in plain English.',
  },
  {
    title: 'Watch it stream',
    line: 'Code types itself into the editor, file by file.',
  },
  {
    title: 'Use it live',
    line: 'The preview runs on your real HighLevel data.',
  },
]

const securityPoints = [
  'Generated apps run in a sandboxed iframe with an opaque origin: no cookies, no storage, no navigation.',
  'Every data request crosses a postMessage bridge and is checked against a server-enforced allowlist.',
  'Your HighLevel tokens live server-side only. The browser, and the generated code, never see them.',
]
</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Nav -->
    <nav
      class="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur"
      aria-label="Main"
    >
      <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <div class="flex items-center gap-2.5">
          <div
            class="flex size-8 items-center justify-center rounded-lg bg-secondary"
            aria-hidden="true"
          >
            <Sparkles class="size-4.5 text-primary" />
          </div>
          <span class="text-[15px] font-semibold tracking-tight">Genesis</span>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="ghost" as-child>
            <RouterLink to="/sign-in">Sign in</RouterLink>
          </Button>
          <Button as-child>
            <RouterLink to="/sign-up">Get started</RouterLink>
          </Button>
        </div>
      </div>
    </nav>

    <main id="main">
      <!-- Hero: asymmetric split -->
      <section class="mx-auto flex min-h-[calc(100dvh-4rem)] max-w-6xl items-center px-6 py-16">
        <div class="grid w-full items-center gap-12 lg:grid-cols-[55fr_45fr]">
          <div class="max-w-xl">
            <h1
              tabindex="-1"
              class="text-4xl leading-[1.1] font-semibold tracking-tight outline-none sm:text-5xl"
            >
              Describe an app.<br />
              Watch it build itself.
            </h1>
            <p class="mt-5 max-w-md text-[15px] leading-relaxed text-muted-foreground">
              Genesis turns plain English into working HighLevel apps, streamed live with your real
              CRM data.
            </p>
            <div class="mt-8 flex items-center gap-3">
              <Button size="lg" as-child>
                <RouterLink to="/sign-up">Get started</RouterLink>
              </Button>
              <Button size="lg" variant="ghost" as-child>
                <RouterLink to="/sign-in">Sign in</RouterLink>
              </Button>
            </div>
          </div>
          <div
            class="relative rounded-xl border border-border bg-card p-1.5 ring-1 ring-white/5 lg:[transform:perspective(1400px)_rotateY(-3deg)]"
          >
            <div class="overflow-hidden rounded-lg">
              <LandingShot
                src="/screenshots/workspace.png"
                alt="The Genesis workspace: chat, code editor, and live preview side by side"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- How it works: connected horizontal strip -->
      <section class="border-t border-border" aria-labelledby="how-heading">
        <div class="mx-auto max-w-6xl px-6 py-20">
          <h2 id="how-heading" class="text-xl font-semibold tracking-tight">How it works</h2>
          <div class="relative mt-10">
            <div class="absolute top-[3px] right-0 left-0 hidden border-t border-border md:block" aria-hidden="true" />
            <ol class="grid gap-8 md:grid-cols-3 md:gap-6">
              <li v-for="step in steps" :key="step.title" class="relative">
                <span
                  class="mb-4 block size-[7px] rounded-full bg-primary"
                  aria-hidden="true"
                />
                <h3 class="text-[15px] font-medium">{{ step.title }}</h3>
                <p class="mt-1.5 max-w-60 text-[13px] leading-relaxed text-muted-foreground">
                  {{ step.line }}
                </p>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <!-- Feature bento: 5 cells, mixed sizes -->
      <section class="border-t border-border" aria-labelledby="features-heading">
        <div class="mx-auto max-w-6xl px-6 py-20">
          <h2 id="features-heading" class="text-xl font-semibold tracking-tight">
            Built like a real dev tool
          </h2>
          <div class="mt-10 grid gap-4 md:grid-cols-6">
            <!-- Big image cell -->
            <div
              class="overflow-hidden rounded-xl border border-border bg-card transition-colors duration-150 hover:border-primary/30 md:col-span-4 md:row-span-2"
            >
              <LandingShot
                src="/screenshots/preview.png"
                alt="A generated contact dashboard showing live HighLevel contacts"
              />
              <div class="p-5">
                <h3 class="text-[15px] font-medium">Real CRM data in the preview</h3>
                <p class="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                  Generated apps read your contacts, conversations, and calendars through a secured
                  proxy. What you see is what ships.
                </p>
              </div>
            </div>
            <!-- Text cells -->
            <div
              class="flex flex-col justify-center rounded-xl border border-border bg-secondary/50 p-6 md:col-span-2"
            >
              <History class="size-5 text-primary" aria-hidden="true" />
              <h3 class="mt-3 text-[15px] font-medium">Snapshots you can trust</h3>
              <p class="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                Every generation is a restorable version. Restores never destroy history.
              </p>
            </div>
            <div
              class="flex flex-col justify-center rounded-xl border border-border bg-card p-6 md:col-span-2"
            >
              <CircleStop class="size-5 text-primary" aria-hidden="true" />
              <h3 class="mt-3 text-[15px] font-medium">Cancel mid-stream</h3>
              <p class="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                Stop a generation at any moment. Finished files stay, half-written ones are rolled
                back.
              </p>
            </div>
            <!-- Wide image cell -->
            <div
              class="overflow-hidden rounded-xl border border-border bg-card transition-colors duration-150 hover:border-primary/30 md:col-span-4"
            >
              <LandingShot
                src="/screenshots/diff.png"
                alt="A side-by-side diff of files changed by a generation"
              />
              <div class="p-5">
                <h3 class="text-[15px] font-medium">Every change reviewable</h3>
                <p class="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                  Side-by-side diffs for every generation, straight from the snapshot history.
                </p>
              </div>
            </div>
            <div
              class="flex flex-col justify-center rounded-xl border border-border bg-secondary/50 p-6 md:col-span-2"
            >
              <ShieldCheck class="size-5 text-primary" aria-hidden="true" />
              <h3 class="mt-3 text-[15px] font-medium">Rate-limited and sandboxed by design</h3>
              <p class="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                Per-user limits on every endpoint. Strict allowlists on every call.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Security statement -->
      <section class="border-t border-border" aria-labelledby="security-heading">
        <div class="mx-auto max-w-6xl px-6 py-20">
          <div class="max-w-3xl">
            <h2 id="security-heading" class="text-2xl font-semibold tracking-tight sm:text-3xl">
              Generated code runs with zero network access.
            </h2>
            <ul class="mt-6 space-y-3">
              <li
                v-for="point in securityPoints"
                :key="point"
                class="flex gap-3 text-[14px] leading-relaxed text-muted-foreground"
              >
                <span class="mt-2 size-1 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                {{ point }}
              </li>
            </ul>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="border-t border-border">
      <div
        class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-[13px] text-muted-foreground"
      >
        <div class="flex items-center gap-2">
          <Sparkles class="size-4 text-primary" aria-hidden="true" />
          <span class="font-medium text-foreground">Genesis</span>
          <span class="ml-2">Built for the HighLevel developer platform</span>
        </div>
        <div class="flex items-center gap-5">
          <a
            href="https://github.com/sattyamjjain/PyVerseAI/tree/main/HighLevel-AI-App-Builder"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-1.5 transition-colors duration-150 hover:text-foreground"
          >
            <Github class="size-4" aria-hidden="true" /> GitHub
          </a>
          <RouterLink to="/sign-in" class="transition-colors duration-150 hover:text-foreground">
            Sign in
          </RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>
