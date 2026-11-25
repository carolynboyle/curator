/**
 * popup-shell.js
 *
 * Generic floating popup for crew dashboards. The shell knows nothing
 * about what a popup shows: it owns the header button, the keyboard
 * shortcut, the floating box, the search box and keyboard navigation.
 * What goes in the list comes from a provider, registered by type.
 *
 * Buttons come from the page (templates/partials/_dashboard_popups.html),
 * one per popup defined in curator.yaml, each carrying its definition as
 * JSON in data-popup:
 *
 *   <button data-popup='{"id":"resources","label":"Resources",
 *           "type":"links","shortcut":"alt+r","project":"..."}'>
 *
 * Provider contract (see popup-links.js for the first one):
 *
 *   registerPopupProvider(type, {
 *     // Fetch what to show. Called every time the popup opens.
 *     async load(config) -> {
 *       items:   [{ label, detail?, ...anything the provider needs }],
 *       message: string,            // shown when items is empty
 *       action:  { label, run } | null,  // optional header button
 *     },
 *     // Called when an item is clicked or chosen with Enter.
 *     select(item, config),
 *   });
 *
 * Only one popup is open at a time. The popup floats and stays open while
 * you work underneath it; Escape or the shortcut closes it. Escape is
 * handled before the detail panel sees it, so closing the popup never
 * also discards the panel.
 */

const providers = new Map();

/** Register the provider that fills popups of the given type. */
export function registerPopupProvider(type, provider) {
  providers.set(type, provider);
}

// ---------------------------------------------------------------------------
// Shortcut parsing — "alt+r" -> { alt, ctrl, shift, meta, code }
// Matching uses KeyboardEvent.code so Option+letter on a Mac (which types a
// different character) still matches, as the panel's own Alt shortcuts do.
// ---------------------------------------------------------------------------

function parseShortcut(text) {
  if (!text) return null;
  const spec = { alt: false, ctrl: false, shift: false, meta: false, code: '' };
  for (const part of String(text).toLowerCase().split('+').map(p => p.trim())) {
    if (part === 'alt' || part === 'option') spec.alt = true;
    else if (part === 'ctrl' || part === 'control') spec.ctrl = true;
    else if (part === 'shift') spec.shift = true;
    else if (part === 'meta' || part === 'cmd') spec.meta = true;
    else if (/^[a-z]$/.test(part)) spec.code = `Key${part.toUpperCase()}`;
    else if (/^[0-9]$/.test(part)) spec.code = `Digit${part}`;
    else if (part === ',') spec.code = 'Comma';
    else if (part === '.') spec.code = 'Period';
    else if (part) spec.code = part;
  }
  return spec.code ? spec : null;
}

function matchesShortcut(event, spec) {
  return !!spec
    && event.code === spec.code
    && event.altKey === spec.alt
    && event.ctrlKey === spec.ctrl
    && event.shiftKey === spec.shift
    && event.metaKey === spec.meta;
}

// ---------------------------------------------------------------------------
// One popup
// ---------------------------------------------------------------------------

class Popup {
  constructor(button, config) {
    this.button = button;
    this.config = config;
    this.shortcut = parseShortcut(config.shortcut);
    this.root = null;       // the floating element while open
    this.items = [];        // everything the provider returned
    this.shown = [];        // items after the search filter
    this.active = -1;       // keyboard-highlighted row in this.shown
    this.token = 0;         // guards against a slow load finishing late
  }

  get isOpen() {
    return this.root !== null;
  }

  async open() {
    this.root = this._build();
    document.body.appendChild(this.root);
    this.button.setAttribute('aria-expanded', 'true');
    this.search.focus();
    await this._load();
  }

  close() {
    this.token += 1;
    this.root?.remove();
    this.root = null;
    this.button.setAttribute('aria-expanded', 'false');
  }

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  }

  // -- DOM ------------------------------------------------------------------

  _build() {
    const root = document.createElement('div');
    root.className = 'popup';
    root.dataset.popupId = this.config.id;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-label', this.config.label);

    const header = document.createElement('div');
    header.className = 'popup-header';
    const title = document.createElement('span');
    title.className = 'popup-title';
    title.textContent = this.config.label;
    this.actionSlot = document.createElement('span');
    this.actionSlot.className = 'popup-action-slot';
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'popup-close';
    closeBtn.setAttribute('aria-label', `Close ${this.config.label}`);
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', () => this.close());
    header.append(title, this.actionSlot, closeBtn);

    this.search = document.createElement('input');
    this.search.type = 'search';
    this.search.className = 'popup-search';
    this.search.placeholder = `Search ${this.config.label.toLowerCase()}…`;
    this.search.autocomplete = 'off';
    this.search.addEventListener('input', () => this._applyFilter());
    this.search.addEventListener('keydown', e => this._onSearchKey(e));

    this.list = document.createElement('ul');
    this.list.className = 'popup-list';
    this.list.setAttribute('role', 'listbox');

    this.status = document.createElement('p');
    this.status.className = 'popup-status';

    root.append(header, this.search, this.list, this.status);
    return root;
  }

  // -- Loading and filtering -------------------------------------------------

  async _load() {
    const provider = providers.get(this.config.type);
    const token = ++this.token;
    this.status.textContent = 'Loading…';
    if (!provider) {
      this.status.textContent = `No provider for popup type "${this.config.type}".`;
      return;
    }
    let result;
    try {
      result = await provider.load(this.config);
    } catch (err) {
      if (token === this.token) this.status.textContent = `Could not load: ${err.message}`;
      return;
    }
    if (token !== this.token) return;   // closed or reopened meanwhile

    this.provider = provider;
    this.items = result.items ?? [];
    this.emptyMessage = result.message || 'Nothing to show.';
    this._setAction(result.action);
    this._applyFilter();
  }

  _setAction(action) {
    this.actionSlot.replaceChildren();
    if (!action) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'popup-action';
    btn.textContent = action.label;
    btn.addEventListener('click', () => {
      this.close();
      action.run();
    });
    this.actionSlot.appendChild(btn);
  }

  _applyFilter() {
    const needle = this.search.value.trim().toLowerCase();
    this.shown = needle
      ? this.items.filter(i => `${i.label ?? ''} ${i.detail ?? ''}`.toLowerCase().includes(needle))
      : this.items.slice();
    this.active = this.shown.length ? 0 : -1;
    this._renderList();
  }

  _renderList() {
    this.list.replaceChildren();
    this.shown.forEach((item, index) => {
      const li = document.createElement('li');
      li.className = 'popup-item';
      li.setAttribute('role', 'option');
      const label = document.createElement('span');
      label.className = 'popup-item-label';
      label.textContent = item.label || '(no label)';
      li.appendChild(label);
      if (item.detail) {
        const detail = document.createElement('span');
        detail.className = 'popup-item-detail';
        detail.textContent = item.detail;
        li.appendChild(detail);
      }
      li.addEventListener('click', () => this._choose(index));
      this.list.appendChild(li);
    });
    this._markActive();

    if (this.shown.length) {
      this.status.textContent = '';
    } else {
      this.status.textContent = this.items.length ? 'No matches.' : this.emptyMessage;
    }
  }

  _markActive() {
    [...this.list.children].forEach((li, index) => {
      const on = index === this.active;
      li.classList.toggle('active', on);
      li.setAttribute('aria-selected', on ? 'true' : 'false');
      if (on) li.scrollIntoView({ block: 'nearest' });
    });
  }

  _choose(index) {
    const item = this.shown[index];
    if (item) this.provider?.select(item, this.config);
  }

  _onSearchKey(e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!this.shown.length) return;
      const step = e.key === 'ArrowDown' ? 1 : -1;
      this.active = (this.active + step + this.shown.length) % this.shown.length;
      this._markActive();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (this.active >= 0) this._choose(this.active);
    }
  }
}

// ---------------------------------------------------------------------------
// Page wiring
// ---------------------------------------------------------------------------

const popups = [];

function openPopup() {
  return popups.find(p => p.isOpen) ?? null;
}

function toggleExclusive(popup) {
  const current = openPopup();
  if (current && current !== popup) current.close();
  popup.toggle();
}

function onKeydown(e) {
  // Escape closes the open popup first; stopping it here keeps the
  // detail panel's own Escape (discard) from firing on the same keypress.
  if (e.key === 'Escape' && openPopup()) {
    e.preventDefault();
    e.stopImmediatePropagation();
    openPopup().close();
    return;
  }
  const hit = popups.find(p => matchesShortcut(e, p.shortcut));
  if (hit) {
    e.preventDefault();
    e.stopImmediatePropagation();
    toggleExclusive(hit);
  }
}

/** Build a Popup for every [data-popup] button on the page. Safe to call once. */
export function initPopups() {
  document.querySelectorAll('button[data-popup]').forEach(button => {
    let config;
    try {
      config = JSON.parse(button.dataset.popup);
    } catch (err) {
      console.warn('Ignoring popup button with unreadable data-popup', err);
      return;
    }
    const popup = new Popup(button, config);
    popups.push(popup);
    button.addEventListener('click', () => toggleExclusive(popup));
  });
  if (popups.length) {
    // Capture phase: runs before the detail panel's bubble-phase listener.
    document.addEventListener('keydown', onKeydown, true);
  }
}

initPopups();
