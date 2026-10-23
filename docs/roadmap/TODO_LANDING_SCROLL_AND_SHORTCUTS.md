# Landing Page — Pinned Illustration and Card Shortcut Keys

**Logged:** 2026-10-23
**Status:** Decided, not built. Build when the crew list outgrows one screen
(more business roles — see `CONFIGURABLE_LANDING_CARDS_DESIGN.md`).

The landing page (2026-10-22 redesign) is two columns on wide screens: the
Curator illustration on the left, crew cards stacked on the right. The
Captain sees every card, so the right column grows with each new role.

---

## 1. Pin the illustration (decided)

When the card list is taller than the window, the page scrolls normally and
the illustration **stays fixed on the left** while the cards move past it.

- `position: sticky` on `.landing .hero-image` (with a `top` offset clear of
  the navbar), wide-screen layout only. ~5 lines in `static/css/layout.css`.
- **No inner scroll box and no visible scrollbars.** Scrolling is the page's
  own (trackpad, wheel, Page Down, space bar); macOS overlay scrollbars stay
  hidden until used. A separate scrolling card column was considered and
  rejected: with its scrollbar hidden, nothing signals that more cards exist.
- Narrow screens (single column, < 900px) keep ordinary scrolling — a pinned
  image would occupy half a phone screen.

## 2. Shortcut letter per card (decided)

Pressing a card's letter on the landing page opens that crew dashboard.

**Assignment rule** (automatic, in card order — earlier cards win):
1. First letter of the role name.
2. If taken, the role name's second letter; then third; and so on.
3. Letters only, case-insensitive; accents folded (í → i).
4. If every letter of the name is taken, the card gets no shortcut.

With today's roles, in order:

| Card | Letter | Why |
|---|---|---|
| The Captain | **C** | first letter |
| The Mechanic | **M** | first letter |
| The Envoy | **E** | first letter |
| The Scribe | **S** | first letter |
| The Seanchaí | **A** | S taken (Scribe), E taken (Envoy) → third letter |

Notes:
- Computed at render time from the card list, so it works whether cards come
  from `curator.yaml` (today) or `identity.landing_card` (future design).
- Consider an optional explicit `shortcut:` override per role, for when the
  automatic letter is unmemorable — not required for the first version.
- Adding a role earlier in the list can change later cards' letters. Keep new
  roles appended, or use the override, if stable letters matter.

**Display:** a small letter badge in a corner of each card (always visible —
no memorising), plus the letter in the card's tooltip.

**Behaviour:**
- Plain key, no modifier — the landing page has no text inputs. Ignore the
  key if Ctrl/Cmd/Alt is held (don't hijack browser shortcuts) or if focus is
  ever in an input.
- Tab moves through the cards with a visible focus ring; Enter opens one
  (native link behaviour — check the focus style is visible in both themes).

## Work involved

- `landing.py`: compute `shortcut` per visible role (rule above), pass to template
- `landing.html`: badge on each card, `data-shortcut` attribute, `title` text
- `layout.css` / `card.css`: sticky image, badge style, focus ring
- ~20 lines of JS on the landing page for the key handler
- Screenshots (desktop + narrow, more than one screen of cards) before committing
