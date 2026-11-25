/**
 * search-summary.js
 *
 * The one-line summary at the top of a search's Details tab. It joins the
 * search's own fields, for example
 *
 *   FamilySearch Full Text · Connell Boyle · Washington County · From 1800 AD
 *
 * so it is clear WHAT was searched, and it keeps itself current as the form
 * is edited. Double-clicking it (or the ↗ button beside it) opens the
 * search's saved Search URL in a new tab, which re-runs the search.
 *
 * Which fields are joined, in what order and with what separator comes from
 * curator.yaml (seanchai: search_summary), delivered by the template as JSON
 * in the wrapper's data-summary:
 *
 *   { "separator": " · ",
 *     "parts": [ {"field": "source"},
 *                {"field": "county_scope", "last_segment": "→"}, ... ] }
 *
 * A part's last_segment keeps only the text after the last occurrence of
 * that string (county scope is a path: "USA → Pennsylvania → Washington").
 * Empty parts are skipped. The URL is read from the form's search_url field.
 *
 * Called from the inline module script in _detail_panel_content.html each
 * time a search panel is swapped in: window.initSearchSummary(wrapper).
 */

import { isSafeUrl, openInTab } from './open-url.js';

const URL_FIELD = 'search_url';

/** The trimmed value of the form control with this name, or ''. */
function fieldValue(form, name) {
  const control = form.elements[name];
  return control && typeof control.value === 'string' ? control.value.trim() : '';
}

/** The text after the last occurrence of `marker`, or the whole text. */
function lastSegment(text, marker) {
  if (!marker) return text;
  const pieces = text.split(marker).map(piece => piece.trim()).filter(Boolean);
  return pieces.length ? pieces[pieces.length - 1] : '';
}

/** Join the configured parts of the form into the summary text. */
export function buildSummary(form, config) {
  const separator = config.separator ?? ' · ';
  return (config.parts ?? [])
    .map(part => lastSegment(fieldValue(form, part.field), part.last_segment))
    .filter(Boolean)
    .join(separator);
}

export function initSearchSummary(root) {
  if (!root) return;
  const form = document.getElementById('detail-form');
  const box = root.querySelector('.search-summary-box');
  const openBtn = root.querySelector('.search-summary-open');
  if (!form || !box || !openBtn) return;

  let config;
  try {
    config = JSON.parse(root.dataset.summary);
  } catch (err) {
    console.warn('Search summary: unreadable data-summary', err);
    return;
  }

  function refresh() {
    box.value = buildSummary(form, config);
    const openable = isSafeUrl(fieldValue(form, URL_FIELD));
    box.classList.toggle('openable', openable);
    box.title = openable
      ? 'Double-click to run this search again'
      : 'Add a Search URL below to run this search again';
    openBtn.disabled = !openable;
  }

  const open = () => openInTab(fieldValue(form, URL_FIELD));
  box.addEventListener('dblclick', open);
  openBtn.addEventListener('click', open);
  // The panel replaces the whole form on each open, so this listener goes
  // away with it; no need to remove it.
  form.addEventListener('input', refresh);

  refresh();
}

window.initSearchSummary = initSearchSummary;
