/**
 * project-links.js
 *
 * Links widget for the project Details tab.
 *
 * Provides two public functions (both exposed on window):
 *
 *   initLinksWidget(widget, projectId)
 *     Full interactive widget — renders list, wires add/select/save/cancel/delete.
 *     Called from the inline <script type="module"> injected by
 *     _detail_panel_content.html each time a project panel is opened.
 *
 *   loadProjectLinks(projectId, container)
 *     Lightweight read-only list loader — mirrors loadTaskList() in
 *     detail-panel.js. Reserved for the future "↗ Links" popup in the
 *     task panel; not used by the embedded widget.
 *
 * State model: currentLinkId tracks whether the edit slot is in "new" mode
 * (null) or "edit existing" mode (integer). allLinks is a local cache so
 * search filtering is instant (no extra round trips).
 */

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function _escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Fetch all links for a project via the generic query API.
 * Returns an array; throws on network or HTTP error.
 */
async function _fetchLinks(projectId) {
  const res = await fetch(
    `/api/query/project_links/for_project?params=${encodeURIComponent(projectId)}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.records ?? data.data ?? []);
}

/**
 * Build a single <li> element for one link.
 *
 * dataset.id / dataset.label / dataset.url carry the raw values so
 * the edit slot can read them on row click without re-fetching.
 * The URL <a> stops click propagation so opening the link doesn't
 * accidentally trigger row selection.
 */
function _buildLinkItem(link) {
  const li = document.createElement('li');
  li.className      = 'links-list-item';
  li.dataset.id     = link.id;
  li.dataset.label  = link.label  ?? '';
  li.dataset.url    = link.url    ?? '';
  li.setAttribute('role', 'option');

  const labelEl = document.createElement('span');
  labelEl.className   = 'links-item-label';
  labelEl.textContent = link.label || '(no label)';
  li.appendChild(labelEl);

  if (link.url) {
    const urlEl = document.createElement('a');
    urlEl.className  = 'links-item-url';
    urlEl.href       = link.url;
    urlEl.target     = '_blank';
    urlEl.rel        = 'noopener noreferrer';
    urlEl.textContent = link.url;
    // Don't let URL click bubble to the list item (which opens edit mode)
    urlEl.addEventListener('click', e => e.stopPropagation());
    li.appendChild(urlEl);
  } else {
    const urlEl = document.createElement('span');
    urlEl.className   = 'links-item-url links-item-url--empty';
    urlEl.textContent = '(no URL yet)';
    li.appendChild(urlEl);
  }

  return li;
}

// ---------------------------------------------------------------------------
// Read-only list loader (for future "↗ Links" popup)
// ---------------------------------------------------------------------------

/**
 * Fetch and render a read-only list of links into `container`.
 * Mirrors detail-panel.js's loadTaskList() — same signature so the
 * future popup can call either interchangeably.
 */
export async function loadProjectLinks(projectId, container) {
  if (!container || !projectId) return;
  container.innerHTML = '<p class="links-list-empty">Loading…</p>';

  try {
    const links = await _fetchLinks(projectId);

    if (links.length === 0) {
      container.innerHTML = '<p class="links-list-empty">No links yet.</p>';
      return;
    }

    const ul = document.createElement('ul');
    ul.className = 'links-list';
    links.forEach(link => ul.appendChild(_buildLinkItem(link)));

    container.innerHTML = '';
    container.appendChild(ul);
  } catch (err) {
    console.error('Could not load links:', err);
    container.innerHTML = '<p class="links-list-empty">Could not load links.</p>';
  }
}

// ---------------------------------------------------------------------------
// Interactive widget
// ---------------------------------------------------------------------------

/**
 * Initialize the embedded links widget inside the project Details tab.
 *
 * Called once per panel open from the inline <script type="module"> in
 * _detail_panel_content.html. Re-called on every panel swap since the
 * entire innerHTML is replaced each time.
 */
export async function initLinksWidget(widget, projectId) {
  if (!widget || !projectId) return;

  // -- DOM refs --
  const addBtn      = widget.querySelector('.links-add-btn');
  const slotSearch  = widget.querySelector('.links-slot-search');
  const slotEdit    = widget.querySelector('.links-slot-edit');
  const searchInput = widget.querySelector('.links-search-input');
  const labelInput  = widget.querySelector('.links-edit-label');
  const urlInput    = widget.querySelector('.links-edit-url');
  const saveBtn     = widget.querySelector('.links-save-btn');
  const cancelBtn   = widget.querySelector('.links-cancel-btn');
  const deleteBtn   = widget.querySelector('.links-delete-btn');
  const listEl      = widget.querySelector('.links-list');

  // -- State --
  let currentLinkId = null;   // null → adding new; integer → editing existing
  let allLinks      = [];     // local cache; search filters this without re-fetching

  // -- List rendering --

  function _renderList(links) {
    listEl.innerHTML = '';

    if (links.length === 0) {
      const empty = document.createElement('li');
      empty.className   = 'links-list-empty';
      empty.textContent = allLinks.length === 0
        ? 'No links yet. Use + Add to create one.'
        : 'No matches.';
      listEl.appendChild(empty);
      return;
    }

    links.forEach(link => {
      const li = _buildLinkItem(link);
      // Highlight already-selected row (e.g. after a save that reloads)
      if (currentLinkId != null && link.id === currentLinkId) {
        li.classList.add('active');
      }
      li.addEventListener('click', () => _selectLink(li, link));
      listEl.appendChild(li);
    });
  }

  async function _loadLinks() {
    try {
      allLinks = await _fetchLinks(projectId);
    } catch (err) {
      console.error('Could not load links:', err);
      allLinks = [];
    }
    _renderList(allLinks);
  }

  // -- State transitions --

  function _showSearch() {
    slotSearch.hidden = false;
    slotEdit.hidden   = true;
    searchInput.value = '';
    currentLinkId     = null;
    listEl.querySelectorAll('.links-list-item').forEach(r => r.classList.remove('active'));
  }

  function _showEdit(label, url, linkId) {
    slotSearch.hidden  = true;
    slotEdit.hidden    = false;
    labelInput.value   = label ?? '';
    urlInput.value     = url   ?? '';
    currentLinkId      = linkId ?? null;
    deleteBtn.hidden   = (linkId == null);
    // Clear any stale constraint from a previous failed save attempt
    labelInput.setCustomValidity('');
    labelInput.focus();
  }

  function _selectLink(li, link) {
    listEl.querySelectorAll('.links-list-item').forEach(r => r.classList.remove('active'));
    li.classList.add('active');
    _showEdit(link.label, link.url, link.id);
  }

  // -- Search filter --

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) { _renderList(allLinks); return; }
    _renderList(
      allLinks.filter(l =>
        (l.label ?? '').toLowerCase().includes(q) ||
        (l.url   ?? '').toLowerCase().includes(q)
      )
    );
  });

  // -- Add button --

  addBtn.addEventListener('click', () => {
    listEl.querySelectorAll('.links-list-item').forEach(r => r.classList.remove('active'));
    _showEdit('', '', null);
  });

  // -- Cancel --

  cancelBtn.addEventListener('click', () => {
    _showSearch();
    _renderList(allLinks);
  });

  // -- Save --

  saveBtn.addEventListener('click', async () => {
    const label = labelInput.value.trim();

    if (!label) {
      labelInput.setCustomValidity('Label is required');
      labelInput.reportValidity();
      return;
    }
    labelInput.setCustomValidity('');

    const body = {
      project_id: projectId,
      label,
      url: urlInput.value.trim() || null,
    };

    const endpoint = currentLinkId != null
      ? `/crew/project_links/${currentLinkId}/save`
      : '/crew/project_links/save';

    try {
      saveBtn.disabled = true;
      const res  = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json();

      if (data.success === false) {
        // Proc-level rejection (e.g. label required, project not found)
        alert(data.message || 'Save failed.');
        return;
      }

      // Success — reload list, return to search state
      await _loadLinks();
      _showSearch();
    } catch (err) {
      console.error('Could not save link:', err);
      alert('Save failed. Please try again.');
    } finally {
      saveBtn.disabled = false;
    }
  });

  // -- Delete --

  deleteBtn.addEventListener('click', async () => {
    if (currentLinkId == null) return;
    // Simple confirm — this is an admin tool, a modal isn't warranted
    if (!confirm('Delete this link?')) return;  // eslint-disable-line no-alert

    try {
      deleteBtn.disabled = true;
      const res = await fetch(`/crew/project_links/${currentLinkId}`, {
        method: 'DELETE',
      });

      if (res.status === 204 || res.ok) {
        await _loadLinks();
        _showSearch();
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.message || 'Delete failed.');
      }
    } catch (err) {
      console.error('Could not delete link:', err);
      alert('Delete failed. Please try again.');
    } finally {
      deleteBtn.disabled = false;
    }
  });

  // -- Initial load --
  await _loadLinks();
}

// ---------------------------------------------------------------------------
// Window exports
// ---------------------------------------------------------------------------

window.initLinksWidget  = initLinksWidget;
window.loadProjectLinks = loadProjectLinks;
