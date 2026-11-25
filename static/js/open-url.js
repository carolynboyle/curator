/**
 * open-url.js
 *
 * The one place that decides whether a stored URL may be opened and opens
 * it. Used by the Documents widget, the dashboard links popup and the
 * search summary box, so "http and https only, in a new tab" is defined
 * once.
 */

/** True only for http(s) URLs — anything else is never opened. */
export function isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url.trim());
}

/** Open a link in a new tab, if it is a safe http(s) URL. */
export function openInTab(url) {
  if (isSafeUrl(url)) window.open(url.trim(), '_blank', 'noopener,noreferrer');
}
