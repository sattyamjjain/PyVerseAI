/**
 * Monaco setup: self-hosted ESM workers (the CDN/AMD path is deprecated
 * upstream since monaco 0.53) + the genesis-dark theme matching the app shell.
 * Import once from main.ts before any editor mounts.
 */
import * as monaco from 'monaco-editor'
import { loader } from '@guolao/vue-monaco-editor'

// monaco 0.56 export-map specifiers (the raw esm/vs paths no longer resolve).
import editorWorker from 'monaco-editor/editor/editor.worker.js?worker'
import jsonWorker from 'monaco-editor/language/json/json.worker.js?worker'
import cssWorker from 'monaco-editor/language/css/css.worker.js?worker'
import htmlWorker from 'monaco-editor/language/html/html.worker.js?worker'
import tsWorker from 'monaco-editor/language/typescript/ts.worker.js?worker'

self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    if (label === 'json') return new jsonWorker()
    if (label === 'css' || label === 'scss' || label === 'less') return new cssWorker()
    if (label === 'html' || label === 'handlebars' || label === 'razor') return new htmlWorker()
    if (label === 'typescript' || label === 'javascript') return new tsWorker()
    return new editorWorker()
  },
}

// Bypass the CDN loader entirely — the bundled instance is the editor.
loader.config({ monaco })

/**
 * Syntax colors target ≥4.5:1 against the #14171d editor surface.
 * Note: the original #5f6b7d comment tone measured below 4.5:1 and was
 * brightened to #7d8798 after the accessibility audit.
 */
monaco.editor.defineTheme('genesis-dark', {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'comment', foreground: '7d8798', fontStyle: 'italic' },
    { token: 'keyword', foreground: '7aa2f7' },
    { token: 'string', foreground: '95d3a2' },
    { token: 'string.html', foreground: '95d3a2' },
    { token: 'number', foreground: 'fbbf24' },
    { token: 'constant', foreground: 'fbbf24' },
    { token: 'identifier', foreground: 'e6e8ee' },
    { token: 'function', foreground: '5fb4f0' },
    { token: 'type', foreground: '38bdf8' },
    { token: 'tag', foreground: 'f7768e' },
    { token: 'attribute.name', foreground: 'e5c07b' },
    { token: 'attribute.value', foreground: '95d3a2' },
    { token: 'delimiter', foreground: '9aa5b5' },
    { token: 'operator', foreground: '9aa5b5' },
  ],
  colors: {
    'editor.background': '#14171d',
    'editor.foreground': '#e6e8ee',
    'editor.lineHighlightBackground': '#ffffff08',
    'editor.selectionBackground': '#fbbf242e',
    'editorCursor.foreground': '#fbbf24',
    'editorLineNumber.foreground': '#7d8798',
    'editorLineNumber.activeForeground': '#99a0ad',
    'editorIndentGuide.background1': '#2b303b',
    'editorWidget.background': '#1f232c',
    'editorWidget.border': '#2b303b',
    'editorSuggestWidget.selectedBackground': '#262b35',
    'scrollbarSlider.background': '#2b303b80',
    'scrollbarSlider.hoverBackground': '#2b303bcc',
    'diffEditor.insertedTextBackground': '#34d39922',
    'diffEditor.removedTextBackground': '#ef444422',
  },
})

export { monaco }

/** Language id from a project file path, for Monaco models. */
export function languageForPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase()
  switch (ext) {
    case 'html':
      return 'html'
    case 'css':
      return 'css'
    case 'js':
      return 'javascript'
    case 'json':
      return 'json'
    case 'svg':
      return 'xml'
    default:
      return 'plaintext'
  }
}
