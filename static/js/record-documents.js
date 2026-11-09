/**
 * record-documents.js
 *
 * Documents widget for the seanchaí record detail panel.
 *
 * A ledger record can span many pages. Each "part" has up to two links:
 * the original image (source_url, e.g. FamilySearch) and a markdown
 * transcription kept in the seanchai repo (md_path, repo-relative).
 *
 * Public function (exposed on window):
 *
 *   initDocsWidget(widget)
 *     Renders the parts list in reading order and wires add / select /
 *     save / cancel / delete. Called from the inline <script type="module">
 *     in _detail_panel_content.html each time a record panel is opened.
 *
 * Reads the record's internal id from widget.dataset.recordId and the
 * repo base URL (for transcription links) from widget.dataset.repoBase.
 * Both come from the server-rendered template, so nothing is hard-coded
 * here. With no repo base configured, a transcription path is shown as
 * plain text instead of a link.
 *
 * Mirrors project-links.js: currentDocId is null in "add" mode and an
 * integer in "edit" mode; allDocs is a local cache of the list.
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** True only for http(s) URLs — anything else is never rendered as a link. */
function _isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim());
}

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

/** Build a small link (or a dimmed placeholder) for one slot of a part. */
function _linkSlot(kind, href, glyph, title) {
  if (!href) {
    const empty = document.createElement('span');
    empty.className = `docs-link docs-link--empty docs-link-${kind}`;
    empty.textContent = glyph;
    empty.title = `No ${title.toLowerCase()} yet`;
    return empty;
  }
  const a = document.createElement('a');
  a.className = `docs-link docs-link-${kind}`;
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  a.textContent = glyph;
  a.title = title;
  // Opening a link must not select the row for editing
  a.addEventListener('click', e => e.stopPropagation());
  return a;
}

/** Build one <li> for a part. Raw values are kept on the element's dataset. */
function _buildItem(doc, repoBase) {
  const li = document.createElement('li');
  li.className = 'docs-item';
  li.dataset.id = doc.id;
  li.setAttribute('role', 'option');

  const seq = document.createElement('span');
  seq.className = 'docs-seq';
  seq.textContent = doc.seq;
  li.appendChild(seq);

  const label = document.createElement('span');
  label.className = 'docs-label';
  label.textContent = doc.label || `Part ${doc.seq}`;
  li.appendChild(label);

  li.appendChild(_linkSlot(
    'source',
    _isSafeUrl(doc.source_url) ? doc.source_url.trim() : null,
    '↗',
    'Original image'
  ));

  const mdHref = _repoUrl(repoBase, doc.md_path);
  if (doc.md_path && !mdHref) {
    // No repo base configured — show the path itself
    const path = document.createElement('span');
    path.className = 'docs-link docs-link-md docs-path';
    path.textContent = doc.md_path;
    li.appendChild(path);
  } else {
    li.appendChild(_linkSlot('md', mdHref, '📄', 'Transcription'));
  }

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
  const addBtn      = widget.querySelector('.docs-add-btn');
  const countEl     = widget.querySelector('.docs-count');
  const listEl      = widget.querySelector('.docs-list');
  const editEl      = widget.querySelector('.docs-edit');
  const labelInput  = widget.querySelector('.docs-edit-label');
  const urlInput    = widget.querySelector('.docs-edit-url');
  const mdInput     = widget.querySelector('.docs-edit-md');
  const statusSel   = widget.querySelector('.docs-edit-status');
  const saveBtn     = widget.querySelector('.docs-save-btn');
  const cancelBtn   = widget.querySelector('.docs-cancel-btn');
  const deleteBtn   = widget.querySelector('.docs-delete-btn');

  // -- State --
  let currentDocId = null;   // null → adding a new part; integer → editing
  let allDocs      = [];

  // -- List rendering --

  function _renderList() {
    listEl.innerHTML = '';
    countEl.textContent = allDocs.length ? `(${allDocs.length})` : '';

    if (allDocs.length === 0) {
      const empty = document.createElement('li');
      empty.className   = 'docs-empty';
      empty.textContent = 'No parts yet. Use + Add part.';
      listEl.appendChild(empty);
      return;
    }

    allDocs.forEach(doc => {
      const li = _buildItem(doc, repoBase);
      if (currentDocId != null && doc.id === currentDocId) li.classList.add('active');
      li.addEventListener('click', () => _select(doc));
      listEl.appendChild(li);
    });
  }

  async function _load() {
    try {
      allDocs = await _fetchDocs(recordId);
    } catch (err) {
      console.error('Could not load document parts:', err);
      allDocs = [];
    }
    _renderList();
  }

  // -- State transitions --

  function _showEdit(doc) {
    editEl.hidden       = false;
    currentDocId        = doc ? doc.id : null;
    labelInput.value    = doc?.label      ?? '';
    urlInput.value      = doc?.source_url ?? '';
    mdInput.value       = doc?.md_path    ?? '';
    statusSel.value     = doc?.status     ?? statusSel.options[0]?.value ?? '';
    deleteBtn.hidden    = (doc == null);
    urlInput.setCustomValidity('');
    labelInput.focus();
  }

  function _hideEdit() {
    editEl.hidden = true;
    currentDocId  = null;
    listEl.querySelectorAll('.docs-item').forEach(r => r.classList.remove('active'));
  }

  function _select(doc) {
    listEl.querySelectorAll('.docs-item').forEach(r =>
      r.classList.toggle('active', Number(r.dataset.id) === doc.id));
    _showEdit(doc);
  }

  // -- Add / cancel --

  addBtn.addEventListener('click', () => {
    listEl.querySelectorAll('.docs-item').forEach(r => r.classList.remove('active'));
    _showEdit(null);
  });

  cancelBtn.addEventListener('click', _hideEdit);

  // -- Save --

  saveBtn.addEventListener('click', async () => {
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
      saveBtn.disabled = true;
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
      _hideEdit();
    } catch (err) {
      console.error('Could not save document part:', err);
      alert('Save failed. Please try again.');
    } finally {
      saveBtn.disabled = false;
    }
  });

  // -- Delete --

  deleteBtn.addEventListener('click', async () => {
    if (currentDocId == null) return;
    if (!confirm('Remove this part?')) return;  // eslint-disable-line no-alert

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
      console.error('Could not delete document part:', err);
      alert('Delete failed. Please try again.');
    } finally {
      deleteBtn.disabled = false;
    }
  });

  // -- Initial load --
  await _load();
}

// ---------------------------------------------------------------------------
// Window exports
// ---------------------------------------------------------------------------

window.initDocsWidget = initDocsWidget;
