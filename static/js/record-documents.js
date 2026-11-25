/**
 * record-documents.js
 *
 * Documents widget for the seanchaí record detail panel.
 *
 * A ledger record can have many documents: the pages of a multi-page deed,
 * or a separate document that belongs with the same record. Each document
 * has up to two links: the original image (source_url, e.g. FamilySearch)
 * and a markdown transcription kept in the seanchai repo (md_path,
 * repo-relative).
 *
 * Public function (exposed on window):
 *
 *   initDocsWidget(widget)
 *     Master-detail: a searchable list of documents on the left, the edit
 *     form on the right. The form is greyed out (its <fieldset> disabled)
 *     until a document is picked or the footer's New button is used. While
 *     the Documents tab is active the footer's Save and New buttons (and
 *     Alt+S / Alt+N) act on documents: the widget registers them with
 *     detail-panel.js (registerFooterHandlers). Called from the inline
 *     <script type="module"> in _detail_panel_content.html each time a
 *     record panel is opened.
 *
 * Reads the record's internal id from widget.dataset.recordId and the
 * repo base URL (for transcription links) from widget.dataset.repoBase.
 * Both come from the server-rendered template, so nothing is hard-coded
 * here. With no repo base configured, the transcription open button stays
 * disabled.
 *
 * State: mode is 'none' (form greyed out), 'add' (new document) or 'edit'
 * (currentDocId is the document's id). A snapshot of the form taken when it
 * is filled lets the widget warn before unsaved edits are thrown away.
 */

import { isSafeUrl as _isSafeUrl, openInTab as _openInTab } from './open-url.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build the link to a transcription file from the repo base and md_path. */
function _repoUrl(base, mdPath) {
  if (!base || !mdPath) return null;
  const root = base.endsWith('/') ? base : `${base}/`;
  const path = mdPath.split('/').map(encodeURIComponent).join('/');
  return `${root}${path}`;
}

async function _fetchDocs(recordId) {
  const res = await fetch(`/seanchai/records/${encodeURIComponent(recordId)}/documents`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/** The label a document shows in the list. */
function _displayLabel(doc) {
  return doc.label || `Document ${doc.seq}`;
}

/** True if the (lower-cased) search text appears in any field of the document. */
function _matches(doc, query) {
  const haystack = [
    _displayLabel(doc),
    doc.source_url,
    doc.md_path,
    (doc.status || '').replace(/_/g, ' '),
  ].join('\n').toLowerCase();
  return haystack.includes(query);
}

/** Build one <li> for a document: sequence number, label, status chip. */
function _buildItem(doc) {
  const li = document.createElement('li');
  li.className = 'docs-item';
  li.dataset.id = doc.id;
  li.tabIndex = 0;
  li.setAttribute('role', 'option');

  const seq = document.createElement('span');
  seq.className = 'docs-seq';
  seq.textContent = doc.seq;
  li.appendChild(seq);

  const label = document.createElement('span');
  label.className = 'docs-label';
  label.textContent = _displayLabel(doc);
  label.title = _displayLabel(doc);
  li.appendChild(label);

  const status = document.createElement('span');
  status.className = `docs-status docs-status--${doc.status}`;
  status.textContent = (doc.status || '').replace(/_/g, ' ');
  li.appendChild(status);

  return li;
}

// ---------------------------------------------------------------------------
// Interactive widget
// ---------------------------------------------------------------------------

export async function initDocsWidget(widget) {
  const recordId = widget?.dataset.recordId;
  if (!widget || !recordId) return;
  const repoBase = widget.dataset.repoBase || '';

  // -- DOM refs --
  const searchInput = widget.querySelector('.docs-search');
  const countEl     = widget.querySelector('.docs-count');
  const listEl      = widget.querySelector('.docs-list');
  const editEl      = widget.querySelector('.docs-edit');       // <fieldset>
  const labelInput  = widget.querySelector('.docs-edit-label');
  const urlInput    = widget.querySelector('.docs-edit-url');
  const mdInput     = widget.querySelector('.docs-edit-md');
  const statusSel   = widget.querySelector('.docs-edit-status');
  const openUrlBtn  = widget.querySelector('.docs-open-url');
  const openMdBtn   = widget.querySelector('.docs-open-md');
  const deleteBtn   = widget.querySelector('.docs-delete-btn');

  // -- State --
  let mode         = 'none';   // 'none' | 'add' | 'edit'
  let currentDocId = null;     // integer in 'edit' mode, otherwise null
  let allDocs      = [];
  let baseline     = '';       // JSON snapshot of the form when it was filled
  let saving       = false;    // a save request is in flight

  // -- Form helpers --

  function _formValues() {
    return JSON.stringify([
      labelInput.value.trim(),
      urlInput.value.trim(),
      mdInput.value.trim(),
      statusSel.value,
    ]);
  }

  function _isDirty() {
    return mode !== 'none' && _formValues() !== baseline;
  }

  /** True if it is fine to leave the current form contents behind. */
  function _confirmDiscard() {
    if (!_isDirty()) return true;
    // eslint-disable-next-line no-alert
    return confirm('This document has changes that have not been saved.\n\n' +
                   'Discard them and continue?');
  }

  function _syncOpenButtons() {
    openUrlBtn.disabled = !_isSafeUrl(urlInput.value);
    const mdHref = _repoUrl(repoBase, mdInput.value.trim());
    openMdBtn.disabled = !_isSafeUrl(mdHref);
    openMdBtn.title = repoBase
      ? 'Open the transcription in the repo'
      : 'No repository URL is configured (seanchai.repo_blob_base)';
  }

  function _markActiveRow() {
    listEl.querySelectorAll('.docs-item').forEach(r =>
      r.classList.toggle('active',
        mode === 'edit' && Number(r.dataset.id) === currentDocId));
  }

  // -- List rendering --

  function _renderList() {
    const query = searchInput.value.trim().toLowerCase();
    const shown = query ? allDocs.filter(d => _matches(d, query)) : allDocs;

    listEl.innerHTML = '';
    if (!allDocs.length) {
      countEl.textContent = '';
    } else if (query) {
      countEl.textContent = `(${shown.length} of ${allDocs.length})`;
    } else {
      countEl.textContent = `(${allDocs.length})`;
    }

    if (!shown.length) {
      const empty = document.createElement('li');
      empty.className   = 'docs-empty';
      empty.textContent = allDocs.length
        ? 'No matching documents.'
        : 'No documents yet. Use New to add one.';
      listEl.appendChild(empty);
      return;
    }

    shown.forEach(doc => {
      const li = _buildItem(doc);
      li.addEventListener('click', () => _select(doc));
      li.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          _select(doc);
        }
      });
      listEl.appendChild(li);
    });
    _markActiveRow();
  }

  async function _load() {
    try {
      allDocs = await _fetchDocs(recordId);
    } catch (err) {
      console.error('Could not load documents:', err);
      allDocs = [];
    }
    _renderList();
  }

  // -- State transitions --

  /** Fill and enable the form: a document to edit, or null to add one. */
  function _showEdit(doc, { focus = true } = {}) {
    mode                = doc ? 'edit' : 'add';
    currentDocId        = doc ? doc.id : null;
    editEl.disabled     = false;
    labelInput.value    = doc?.label      ?? '';
    urlInput.value      = doc?.source_url ?? '';
    mdInput.value       = doc?.md_path    ?? '';
    statusSel.value     = doc?.status     ?? statusSel.options[0]?.value ?? '';
    deleteBtn.hidden    = (doc == null);
    urlInput.setCustomValidity('');
    baseline = _formValues();
    _syncOpenButtons();
    _markActiveRow();
    window.syncFooterState?.();
    if (focus) labelInput.focus();
  }

  /** Clear the form and grey it out. */
  function _hideEdit() {
    mode             = 'none';
    currentDocId     = null;
    labelInput.value = '';
    urlInput.value   = '';
    mdInput.value    = '';
    statusSel.value  = statusSel.options[0]?.value ?? '';
    urlInput.setCustomValidity('');
    deleteBtn.hidden = true;
    editEl.disabled  = true;
    baseline = _formValues();
    _syncOpenButtons();
    _markActiveRow();
    window.syncFooterState?.();
  }

  function _select(doc) {
    if (mode === 'edit' && currentDocId === doc.id) return;
    if (!_confirmDiscard()) return;
    _showEdit(doc);
  }

  // -- Search --

  searchInput.addEventListener('input', _renderList);

  // -- New (footer New button / Alt+N) --

  function _newDoc() {
    if (mode === 'add' && !_isDirty()) {
      labelInput.focus();
      return;
    }
    if (!_confirmDiscard()) return;
    _showEdit(null);
  }

  // -- Open links in a new tab --
  // Double-click the URL box, or use the ↗ / 📄 buttons. These open whatever
  // is in the box (saved or not); only http(s) URLs are launched.

  urlInput.addEventListener('dblclick', () => _openInTab(urlInput.value));
  openUrlBtn.addEventListener('click', () => _openInTab(urlInput.value));
  openMdBtn.addEventListener('click', () =>
    _openInTab(_repoUrl(repoBase, mdInput.value.trim())));
  urlInput.addEventListener('input', _syncOpenButtons);
  mdInput.addEventListener('input', _syncOpenButtons);

  // -- Save --

  async function _saveDoc() {
    if (saving || mode === 'none') return;
    const sourceUrl = urlInput.value.trim();
    const mdPath    = mdInput.value.trim();

    if (!sourceUrl && !mdPath) {
      urlInput.setCustomValidity('Enter a source URL, a transcription path, or both');
      urlInput.reportValidity();
      return;
    }
    urlInput.setCustomValidity('');

    const body = {
      label:      labelInput.value.trim(),
      source_url: sourceUrl,
      md_path:    mdPath,
      status:     statusSel.value,
    };
    if (currentDocId == null) body.record_id = recordId;

    const endpoint = currentDocId != null
      ? `/seanchai/record_documents/${currentDocId}/save`
      : '/seanchai/record_documents/save';

    try {
      saving = true;
      const res  = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      if (data.success === false) {
        alert(data.message || 'Save failed.');
        return;
      }

      await _load();
      // Keep the saved document selected (it also re-baselines the form)
      const saved = allDocs.find(d => d.id === Number(data.id));
      if (saved) _showEdit(saved, { focus: false });
      else _hideEdit();
    } catch (err) {
      console.error('Could not save document:', err);
      alert('Save failed. Please try again.');
    } finally {
      saving = false;
    }
  }

  // -- Delete --

  deleteBtn.addEventListener('click', async () => {
    if (currentDocId == null) return;
    if (!confirm('Remove this document?')) return;  // eslint-disable-line no-alert

    try {
      deleteBtn.disabled = true;
      const res = await fetch(`/seanchai/record_documents/${currentDocId}`, {
        method: 'DELETE',
      });

      if (res.status === 204 || res.ok) {
        await _load();
        _hideEdit();
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.message || 'Delete failed.');
      }
    } catch (err) {
      console.error('Could not delete document:', err);
      alert('Delete failed. Please try again.');
    } finally {
      deleteBtn.disabled = false;
    }
  });

  // -- Footer: Save / New (and Alt+S / Alt+N) act on documents while this tab is active --

  window.registerFooterHandlers?.(widget.closest('.detail-tab-panel'), {
    save:         _saveDoc,
    new:          _newDoc,
    canSave:      () => mode !== 'none' && !saving,
    isDirty:      _isDirty,
    dirtyMessage: 'This document has changes that have not been saved.\n\n' +
                  'Discard them and close?',
  });

  // -- Initial state: greyed-out form, then the list --
  _hideEdit();
  await _load();
}

// ---------------------------------------------------------------------------
// Window exports
// ---------------------------------------------------------------------------

window.initDocsWidget = initDocsWidget;
