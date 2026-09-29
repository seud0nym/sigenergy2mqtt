/** Reconcile freshly loaded server state with the editors already on screen.
 *
 * Kept separate from the dashboard bootstrap so the reload behaviour can be
 * exercised without a browser. Dirty editors are deliberately never passed
 * to setEditorValue, which preserves their unapplied text verbatim.
 */
export function reconcileEditors(values, state, createCard, setEditorValue) {
  const existing = new Map(
    [...values.children].map(element => [element.dataset.name, element])
  );
  let preserved = 0;
  for (const [name, value] of Object.entries(state)) {
    const article = existing.get(name);
    if (!article) {
      values.append(createCard(name, value));
      continue;
    }
    const textarea = article.querySelector('textarea');
    if (textarea.dataset.dirty === 'true') preserved += 1;
    else setEditorValue(textarea, value);
  }
  return preserved;
}

/** Attach the dashboard reload action (exported so tests can click it). */
export function bindReload(button, reload) {
  button.addEventListener('click', reload);
}
