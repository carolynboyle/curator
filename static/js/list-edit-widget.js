/**
 * list-edit-widget.js
 *
 * Generic list-and-edit widget for a detail panel tab: a searchable list of
 * child items on the left, an edit form on the right. It knows nothing about
 * documents or links; everything specific comes from a definition in
 * curator.yaml's list_edit_tabs (curator/list_edit.py), rendered into the
 * page by partials/_list_edit_widget.html as JSON in data-definition.
 *
 * Public function (exposed on window):
 *
 *   initListEditWidget(root)
 *     Called from the inline <script type="module"> the partial emits each
 *     time a panel is opened. The form is greyed out (its <fieldset>
 *     disabled) until an item is picked or the footer's New button is used.
 *     While the tab is active the footer's Save and New buttons (and Alt+S /
 *     Alt+N) act on its items: the widget registers them with detail-panel.js
 *     (registerFooterHandlers).
 *
 * Reads the parent's id from root.dataset.parentId and the definition from
 * root.dataset.definition. Fields are found by [data-field="name"]; the
 * open-in-a-new-tab buttons by [data-open-for="name"].
 *
 * State: mode is 'none' (form greyed out), 'add' (new item) or 'edit'
 * (currentId is the item's id). A snapshot of the form taken when it is
 * filled lets the widget warn before unsaved edits are thrown away.
 */

import { isSafeUrl, openInTab } from './open-url.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Join a base URL and a path (each path segment encoded); null if either is empty. */
function _repoUrl(base, path) {
  if (!base || !path) return null;
  const root = base.endsWith('/') ? base : `${base}/`;
  return `${root}${path.split('/').map(encodeURIComponent).join('/')}`;
}

/** Fill {field} placeholders in a template from an item. */
function _fill(template, item) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => item[key] ?? '');
}

/** A value as the text a person reads: nothing for null, underscores as spaces. */
function _readable(value) {
  return value == null ? '' : String(value).replace(/_/g, ' ');
}

/** Fetch the list for a parent; accepts a bare array or {records|data: [...]}. */
async function _fetchItems(def, parentId) {
  const url = def.list_url.replace('{parent_id}', encodeURIComponent(parentId));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  if (Array.isArray(data)) return data;
  return data.records ?? data.data ?? [];
}

// ---------------------------------------------------------------------------
// Interactive widget
// ---------------------------------------------------------------------------

export async function initListEditWidget(root) {
  const parentId = root?.dataset.parentId;
  if (!root || !parentId) return;
  const def = JSON.parse(root.dataset.definition);
  const noun = def.noun;
  const label = def.label.toLowerCase();

  // -- DOM refs --
  const searchInput = root.querySelector('.le-search');
  const countEl     = root.querySelector('.le-count');
  const listEl      = root.querySelector('.le-list');
  const editEl      = root.querySelector('.le-edit');          // <fieldset>
  const deleteBtn   = root.querySelector('.le-delete-btn');
  const inputs = {};
  def.fields.forEach(f => {
    inputs[f.name] = root.querySelector(`[data-field="${f.name}"]`);
  });
  const openFields = def.fields.filter(f => f.open);
  const openButtons = {};
  openFields.forEach(f => {
    openButtons[f.name] = root.querySelector(`[data-open-for="${f.name}"]`);
  });

  // -- State --
  let mode      = 'none';   // 'none' | 'add' | 'edit'
  let currentId = null;     // integer in 'edit' mode, otherwise null
  let allItems  = [];
  let baseline  = '';       // JSON snapshot of the form when it was filled
  let saving    = false;    // a save request is in flight

  // -- Form helpers --

  function _defaultValue(field) {
    const input = inputs[field.name];
    return field.control === 'select' ? (input.options[0]?.value ?? '') : '';
  }

  function _formValues() {
    return JSON.stringify(def.fields.map(f => inputs[f.name].value.trim()));
  }

  function _isDirty() {
    return mode !== 'none' && _formValues() !== baseline;
  }

  /** True if it is fine to leave the current form contents behind. */
  function _confirmDiscard() {
    if (!_isDirty()) return true;
    // eslint-disable-next-line no-alert
    return confirm(`This ${noun} has changes that have not been saved.\n\n` +
                   'Discard them and continue?');
  }

  /** The field that carries the "at least one of these" message, if any. */
  function _requireField() {
    const names = def.require_one_of?.fields;
    return names?.length ? inputs[names[0]] : null;
  }

  function _clearValidity() {
    def.fields.forEach(f => inputs[f.name].setCustomValidity(''));
  }

  /** What an open button would launch for a field right now (or null). */
  function _openTarget(field) {
    const value = inputs[field.name].value.trim();
    return field.open === 'repo' ? _repoUrl(def.repo_base, value) : value;
  }

  function _syncOpenButtons() {
    openFields.forEach(f => {
      const btn = openButtons[f.name];
      btn.disabled = !isSafeUrl(_openTarget(f));
      if (f.open === 'repo' && !def.repo_base) {
        btn.title = 'No repository URL is configured';
      }
    });
  }

  function _markActiveRow() {
    listEl.querySelectorAll('.le-item').forEach(r =>
      r.classList.toggle('active',
        mode === 'edit' && Number(r.dataset.id) === currentId));
  }

  // -- List rendering --

  /** The name an item shows in the list. */
  function _title(item) {
    return item[def.title_field] || _fill(def.title_fallback ?? '', item);
  }

  /** True if the (lower-cased) query appears in any searchable field. */
  function _matches(item, query) {
    const parts = [_title(item)];
    (def.search_fields ?? []).forEach(name => {
      const value = item[name];
      if (value == null) return;
      parts.push(String(value), _readable(value));   // typed as stored or as shown
    });
    return parts.join('\n').toLowerCase().includes(query);
  }

  function _span(className, text) {
    const el = document.createElement('span');
    el.className = className;
    el.textContent = text;
    return el;
  }

  /** Build one <li>: optional prefix, name (and subtitle), optional chip. */
  function _buildItem(item) {
    const li = document.createElement('li');
    li.className = 'le-item';
    li.dataset.id = item.id;
    li.tabIndex = 0;
    li.setAttribute('role', 'option');

    if (def.prefix_field && item[def.prefix_field] != null) {
      li.appendChild(_span('le-prefix', item[def.prefix_field]));
    }

    const text = document.createElement('span');
    text.className = 'le-text';
    const title = _span('le-title', _title(item));
    title.title = _title(item);
    text.appendChild(title);
    if (def.subtitle_field && item[def.subtitle_field]) {
      text.appendChild(_span('le-subtitle', item[def.subtitle_field]));
    }
    li.appendChild(text);

    if (def.badge_field && item[def.badge_field]) {
      const tone = def.badge_tones?.[item[def.badge_field]];
      li.appendChild(_span(
        tone ? `le-badge le-badge--${tone}` : 'le-badge',
        _readable(item[def.badge_field])));
    }
    return li;
  }

  function _renderList() {
    const query = searchInput.value.trim().toLowerCase();
    const shown = query ? allItems.filter(i => _matches(i, query)) : allItems;

    listEl.innerHTML = '';
    if (!allItems.length) {
      countEl.textContent = '';
    } else if (query) {
      countEl.textContent = `(${shown.length} of ${allItems.length})`;
    } else {
      countEl.textContent = `(${allItems.length})`;
    }

    if (!shown.length) {
      const empty = document.createElement('li');
      empty.className   = 'le-empty';
      empty.textContent = allItems.length ? `No matching ${label}.` : def.empty_text;
      listEl.appendChild(empty);
      return;
    }

    shown.forEach(item => {
      const li = _buildItem(item);
      li.addEventListener('click', () => _select(item));
      li.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          _select(item);
        }
      });
      listEl.appendChild(li);
    });
    _markActiveRow();
  }

  async function _load() {
    try {
      allItems = await _fetchItems(def, parentId);
    } catch (err) {
      console.error(`Could not load ${label}:`, err);
      allItems = [];
    }
    _renderList();
  }

  // -- State transitions --

  /** Fill and enable the form: an item to edit, or null to add one. */
  function _showEdit(item, { focus = true } = {}) {
    mode            = item ? 'edit' : 'add';
    currentId       = item ? item.id : null;
    editEl.disabled = false;
    def.fields.forEach(f => {
      inputs[f.name].value = item?.[f.name] ?? _defaultValue(f);
    });
    deleteBtn.hidden = (item == null);
    _clearValidity();
    baseline = _formValues();
    _syncOpenButtons();
    _markActiveRow();
    window.syncFooterState?.();
    if (focus) inputs[def.fields[0].name].focus();
  }

  /** Clear the form and grey it out. */
  function _hideEdit() {
    mode      = 'none';
    currentId = null;
    def.fields.forEach(f => { inputs[f.name].value = _defaultValue(f); });
    _clearValidity();
    deleteBtn.hidden = true;
    editEl.disabled  = true;
    baseline = _formValues();
    _syncOpenButtons();
    _markActiveRow();
    window.syncFooterState?.();
  }

  function _select(item) {
    if (mode === 'edit' && currentId === item.id) return;
    if (!_confirmDiscard()) return;
    _showEdit(item);
  }

  // -- Search --

  searchInput.addEventListener('input', _renderList);

  // -- New (footer New button / Alt+N) --

  function _newItem() {
    if (mode === 'add' && !_isDirty()) {
      inputs[def.fields[0].name].focus();
      return;
    }
    if (!_confirmDiscard()) return;
    _showEdit(null);
  }

  // -- Open links in a new tab --
  // Double-click a link box, or use its ↗ / 📄 button. These open whatever is
  // in the box (saved or not); only http(s) URLs are launched.

  openFields.forEach(f => {
    const input = inputs[f.name];
    input.addEventListener('input', _syncOpenButtons);
    openButtons[f.name].addEventListener('click', () => openInTab(_openTarget(f)));
    if (f.open === 'url') {
      input.addEventListener('dblclick', () => openInTab(_openTarget(f)));
    }
  });

  // -- Save --

  /** Reject the save with a message on a field; true if all is well. */
  function _validate() {
    _clearValidity();

    const missing = def.fields.find(f => f.required && !inputs[f.name].value.trim());
    if (missing) {
      inputs[missing.name].setCustomValidity(`${missing.label} is required`);
      inputs[missing.name].reportValidity();
      return false;
    }

    const rule = def.require_one_of;
    if (rule && !rule.fields.some(n => inputs[n].value.trim())) {
      const target = _requireField();
      target.setCustomValidity(rule.message || 'Fill in at least one of these fields');
      target.reportValidity();
      return false;
    }
    return true;
  }

  /** The existing item a new one would repeat (per duplicate_of), or null. */
  function _duplicateOfExisting() {
    const names = def.duplicate_of;
    if (!names?.length || mode !== 'add') return null;
    const same = (a, b) => String(a ?? '').trim().toLowerCase() === String(b ?? '').trim().toLowerCase();
    return allItems.find(item => names.every(n => same(item[n], inputs[n].value))) ?? null;
  }

  async function _saveItem() {
    if (saving || mode === 'none') return;
    if (!_validate()) return;

    const dupe = _duplicateOfExisting();
    // eslint-disable-next-line no-alert
    if (dupe && !confirm(`This looks the same as a ${noun} you already have ` +
                         `("${_title(dupe)}").\n\nSave it anyway?`)) return;

    const body = {};
    def.fields.forEach(f => { body[f.name] = inputs[f.name].value.trim(); });
    if (currentId == null) body[def.parent_key] = parentId;

    const endpoint = currentId != null
      ? def.save_url.replace('{id}', currentId)
      : def.save_new_url;

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
      // Keep the saved item selected (it also re-baselines the form)
      const saved = allItems.find(i => i.id === Number(data.id));
      if (saved) _showEdit(saved, { focus: false });
      else _hideEdit();
    } catch (err) {
      console.error(`Could not save ${noun}:`, err);
      alert('Save failed. Please try again.');
    } finally {
      saving = false;
    }
  }

  // -- Delete --

  deleteBtn.addEventListener('click', async () => {
    if (currentId == null) return;
    if (!confirm(`Remove this ${noun}?`)) return;  // eslint-disable-line no-alert

    try {
      deleteBtn.disabled = true;
      const res = await fetch(def.delete_url.replace('{id}', currentId), {
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
      console.error(`Could not delete ${noun}:`, err);
      alert('Delete failed. Please try again.');
    } finally {
      deleteBtn.disabled = false;
    }
  });

  // -- Footer: Save / New (and Alt+S / Alt+N) act on this tab's items while it is active --

  window.registerFooterHandlers?.(root.closest('.detail-tab-panel'), {
    save:         _saveItem,
    new:          _newItem,
    canSave:      () => mode !== 'none' && !saving,
    isDirty:      _isDirty,
    dirtyMessage: `This ${noun} has changes that have not been saved.\n\n` +
                  'Discard them and close?',
  });

  // -- Initial state: greyed-out form, then the list --
  _hideEdit();
  await _load();
}

// ---------------------------------------------------------------------------
// Window exports
// ---------------------------------------------------------------------------

window.initListEditWidget = initListEditWidget;
