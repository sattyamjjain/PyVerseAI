import MarkdownItCtor from 'markdown-it'
import type { MarkdownIt, RendererRule } from 'markdown-it'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'

hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('css', css)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const md: MarkdownIt = new MarkdownItCtor({
  html: false, // LLM output is never treated as HTML
  linkify: true,
  breaks: false,
  highlight(code: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
      } catch {
        /* fall through to escape */
      }
    }
    return escapeHtml(code)
  },
})

// External links open safely in a new tab.
const defaultLinkOpen: RendererRule =
  md.renderer.rules.link_open ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx]!.attrSet('target', '_blank')
  tokens[idx]!.attrSet('rel', 'noopener noreferrer')
  tokens[idx]!.attrSet('title', 'Opens in new tab')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

// Fenced code blocks get a header strip (language label + copy button).
// The copy button carries no handler — ChatMarkdown handles clicks by
// delegation and reads the sibling <code> text.
const defaultFence: RendererRule =
  md.renderer.rules.fence ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
  const token = tokens[idx]!
  const lang = (token.info || '').trim().split(/\s+/)[0] || 'text'
  const body = defaultFence(tokens, idx, options, env, self)
  return `<div class="code-block"><div class="code-block-header"><span>${escapeHtml(lang)}</span><button type="button" class="code-copy" aria-label="Copy code">Copy</button></div>${body}</div>`
}

/** Render LLM/chat markdown to sanitized HTML (the app's single v-html source). */
export function renderMarkdown(src: string): string {
  return DOMPurify.sanitize(md.render(src), {
    USE_PROFILES: { html: true },
    ADD_ATTR: ['target', 'rel'],
  })
}
