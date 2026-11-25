/**
 * popup-links.js
 *
 * Provider for popups of type "links": shows the Links list of one project
 * (the same links you edit on a project's Details tab) as a searchable
 * list. Clicking a link opens it in a new tab.
 *
 * Popup config (curator.yaml, see popups.py):
 *   project   slug of the project whose links to show, e.g.
 *             "genealogy-resources"
 *
 * The slug is looked up with queries.yaml project_links/for_project_slug,
 * which returns one row per link, or a single row with no link when the
 * project has none; no rows at all means the slug doesn't exist.
 */

import { registerPopupProvider } from './popup-shell.js';
import { openInTab } from './open-url.js';

async function fetchRows(slug) {
  const res = await fetch(
    `/api/query/project_links/for_project_slug?params=${encodeURIComponent(slug)}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data) ? data : (data.records ?? []);
}

registerPopupProvider('links', {
  async load(config) {
    if (!config.project) {
      return { items: [], message: 'No project set for this popup.', action: null };
    }
    const rows = await fetchRows(config.project);
    if (!rows.length) {
      return {
        items: [],
        message: `Project not found: ${config.project}`,
        action: null,
      };
    }

    const projectId = rows[0].project_id;
    const items = rows
      .filter(row => row.id !== null && row.id !== undefined)
      .map(row => ({ label: row.label, detail: row.url ?? '', url: row.url ?? '' }));

    return {
      items,
      message: 'No links yet.',
      action: {
        label: 'Manage links',
        run: () => window.openDetailPanel?.('projects', projectId),
      },
    };
  },

  select(item) {
    openInTab(item.url);
  },
});
