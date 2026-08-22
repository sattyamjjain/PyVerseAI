/**
 * Monaco text-model registry. Models live independently of any mounted editor,
 * so generation streaming can append to files that aren't currently visible.
 */
import { monaco, languageForPath } from '@/lib/monaco'

const models = new Map<string, ReturnType<typeof monaco.editor.createModel>>()

export function getModel(path: string) {
  return models.get(path) ?? null
}

export function getOrCreateModel(path: string, content = '') {
  let model = models.get(path)
  if (!model || model.isDisposed()) {
    model = monaco.editor.createModel(content, languageForPath(path))
    models.set(path, model)
  }
  return model
}

/** Replace content without nuking the undo stack (single edit operation). */
export function setModelValue(path: string, content: string) {
  const model = getOrCreateModel(path)
  if (model.getValue() === content) return
  model.pushEditOperations(
    [],
    [{ range: model.getFullModelRange(), text: content }],
    () => null,
  )
}

export function appendToModel(path: string, text: string) {
  const model = getOrCreateModel(path)
  const end = model.getFullModelRange().getEndPosition()
  model.applyEdits([
    { range: new monaco.Range(end.lineNumber, end.column, end.lineNumber, end.column), text },
  ])
}

export function pushUndoStop(path: string) {
  models.get(path)?.pushStackElement()
}

export function disposeModel(path: string) {
  models.get(path)?.dispose()
  models.delete(path)
}

export function disposeAllModels() {
  for (const model of models.values()) model.dispose()
  models.clear()
}
