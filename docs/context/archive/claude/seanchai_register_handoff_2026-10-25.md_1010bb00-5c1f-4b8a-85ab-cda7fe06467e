# Seanchaí Register — Handoff 2026-10-25

**Picks up from:** `seanchai_register_handoff_2026-10-22.md`  
**Status:** Approach approved, repos confirmed, file numbers confirmed. Nothing built yet. Ready to write SQL.

---

## Current state

### Repos (all cloned and confirmed in the 2026-10-25 session)

| Repo | GitHub | Local clone |
|---|---|---|
| steward | `carolynboyle/steward` | `/home/claude/steward` (on VPS: `~/projects/steward`) |
| curator | `carolynboyle/curator` | `/home/claude/curator` |
| seanchai | `carolynboyle/seanchai` | `/home/claude/seanchai` |

The steward SQL lives at `databases/wcyj/sql/`.

### Last steward SQL applied on live DB

Through `10i_seanchai_todos_to_tasks.sql`. Since the 10-22 handoff, one more file was committed:  
`10j_seanchai_task_records_api.sql` — `api.get_task_linked_records()` for the Curator task panel linked-records widget.

**Next free number: `10k`.**

### seanchaí → seanchai consolidation (not yet done)

`~/projects/seanchaí` is a local-only folder (no GitHub). Contents:

- `data/full-ledger-export.json` — identical to `seanchai/data/ledger_export_2026-10-22.json` (same 328,832 bytes). Discard.
- `docs/ledger-structure-inventory.md` — 13KB structural analysis of the original artifact database (field quirks, relationship patterns, schema recommendations). **Worth keeping.** Should go to `seanchai/docs/ledger-structure-inventory.md`.

**To do:** copy `ledger-structure-inventory.md` into `seanchai/docs/`, commit, push. Then tell Carolyn she can delete `~/projects/seanchaí/`.

---

## Approved approach (unchanged from 10-22 handoff)

Port the Register's HTML/CSS/JS into a **Register tab on the Seanchaí crew dashboard**, loading from PostgreSQL instead of hardcoded JS arrays. Edit forms save through `api.*` functions. "Generate Export → copy to Claude" loop ends.

Three steps (build in order, deploy step 1 before starting step 2):

1. **Schema + seed** — two steward SQL files, tested on scratch Postgres 16
2. **Read-only Register tab in Curator** — Jinja2 partial + JS + JSON API routes
3. **Edit forms** wired to `api.save_person` / `api.save_place`

**Do not touch the artifact until the Curator version matches it.**

---

## Step 1 build plan

### Files to create

**`steward/databases/wcyj/sql/10k_seanchai_register_schema.sql`**  
Nine new tables in the `seanchai` schema. See schema section below.

**`steward/databases/wcyj/sql/10l_seanchai_register_seed.sql`**  
INSERT for all 25 people, 21 places, ~175 events, all relationships, tags, and associations.  
Source of truth: the Register artifact at `https://claude.ai/artifact/U6ubhT3cx4TXqg58bik4dR`.  
Read it with `Artifact(action="read", url="https://claude.ai/artifact/U6ubhT3cx4TXqg58bik4dR")` to extract the data.

**`seanchai/data/register_export_2026-10-25.json`**  
Raw JSON of all people + places data extracted from the artifact. Kept as the source of record for the one-time load, same pattern as `ledger_export_2026-10-22.json`. Generate this alongside the seed SQL.

### Testing

Test `10k` + `10l` together on scratch Postgres 16 using the full steward chain:
- Build order: every file in name order, **skip `05b_migration_app_user.sql`**, run `07a_detail_views.sql` **before** `07b_detail_api.sql`
- After `10l` applies cleanly with no errors: confirm row counts match (25 people, 21 places)

### Deployment (Carolyn runs on VPS after testing passes)

```bash
# From ~/projects/curator (docker-compose.yml lives there)
docker compose exec -T db psql -U steward -d wcyj -v ON_ERROR_STOP=1 \
  < ~/projects/steward/databases/wcyj/sql/10k_seanchai_register_schema.sql

docker compose exec -T db psql -U steward -d wcyj -v ON_ERROR_STOP=1 \
  < ~/projects/steward/databases/wcyj/sql/10l_seanchai_register_seed.sql
```

No GRANT needed for read-only tables until the `api.*` functions are added in Step 3.  
*(Actually: re-check this — `web_app_user` needs SELECT on the tables for the JSON routes. Add explicit GRANTs at the end of `10k` for all nine tables.)*

---

## Schema — `10k_seanchai_register_schema.sql`

### Tables

```sql
-- People
CREATE TABLE seanchai.people (
    id          SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,         -- e.g. 'phelim-oboyle'
    name        TEXT NOT NULL,
    alt_name    TEXT,
    person_group TEXT NOT NULL,               -- sidebar section heading
    born_year   TEXT,                         -- 'c. 1748', '1773 or 1777'
    born_place  TEXT,
    died_year   TEXT,
    died_place  TEXT,
    notes       TEXT
);

-- Places
CREATE TABLE seanchai.places (
    id               SERIAL PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,    -- e.g. 'romania-farm'
    name             TEXT NOT NULL,
    alt_name         TEXT,
    place_group      TEXT NOT NULL,           -- sidebar section heading
    place_type       TEXT,                    -- 'farm', 'township', 'city', etc.
    loc_area         TEXT,
    loc_county       TEXT,
    loc_state        TEXT,
    loc_country      TEXT,
    established_year TEXT,
    established_note TEXT,
    status_year      TEXT,
    status_note      TEXT,
    current_status   TEXT,
    notes            TEXT
);

-- Events (one row per event per person)
CREATE TABLE seanchai.person_events (
    id          SERIAL PRIMARY KEY,
    person_id   INTEGER NOT NULL REFERENCES seanchai.people(id) ON DELETE CASCADE,
    event_year  TEXT NOT NULL,
    event_text  TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Events (one row per event per place)
CREATE TABLE seanchai.place_events (
    id          SERIAL PRIMARY KEY,
    place_id    INTEGER NOT NULL REFERENCES seanchai.places(id) ON DELETE CASCADE,
    event_year  TEXT NOT NULL,
    event_text  TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Person↔Person relationships
-- All four directions stored as stated in the artifact (parent/child/spouse/sibling)
CREATE TABLE seanchai.person_relationships (
    person_id   INTEGER NOT NULL REFERENCES seanchai.people(id) ON DELETE CASCADE,
    related_id  INTEGER NOT NULL REFERENCES seanchai.people(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL CHECK (kind IN ('parent','child','spouse','sibling')),
    PRIMARY KEY (person_id, related_id, kind)
);

-- Person↔Place associations (associatedPlaces / associatedPeople)
CREATE TABLE seanchai.person_place_assoc (
    person_id   INTEGER NOT NULL REFERENCES seanchai.people(id) ON DELETE CASCADE,
    place_id    INTEGER NOT NULL REFERENCES seanchai.places(id) ON DELETE CASCADE,
    PRIMARY KEY (person_id, place_id)
);

-- Place↔Place relations
CREATE TABLE seanchai.place_relations (
    place_id    INTEGER NOT NULL REFERENCES seanchai.places(id) ON DELETE CASCADE,
    related_id  INTEGER NOT NULL REFERENCES seanchai.places(id) ON DELETE CASCADE,
    PRIMARY KEY (place_id, related_id)
);

-- Tags (junction tables — consistent with rest of schema)
CREATE TABLE seanchai.person_tags (
    person_id   INTEGER NOT NULL REFERENCES seanchai.people(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    PRIMARY KEY (person_id, tag)
);

CREATE TABLE seanchai.place_tags (
    place_id    INTEGER NOT NULL REFERENCES seanchai.places(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    PRIMARY KEY (place_id, tag)
);
```

### GRANTs (end of `10k`)

```sql
GRANT SELECT ON
    seanchai.people,
    seanchai.places,
    seanchai.person_events,
    seanchai.place_events,
    seanchai.person_relationships,
    seanchai.person_place_assoc,
    seanchai.place_relations,
    seanchai.person_tags,
    seanchai.place_tags
TO web_app_user;
```

---

## Data — what to extract from the artifact

Read `https://claude.ai/artifact/U6ubhT3cx4TXqg58bik4dR` with the Artifact tool.  
The artifact contains hardcoded `PEOPLE` (25 records) and `PLACES` (21 records) JS arrays.

### People (25 records in 5 groups)

| Group | Slugs |
|---|---|
| Boyle — Donegal Line | `phelim-oboyle`, `ann-rice`, `felix-sr-boyle`, `connell-boyle`, `john-boyle-1804`, `maria-boyle` |
| Beall Line | `major-zephaniah-beall`, `zephaniah-beall-esq`, `mary-purcell`, `rebecca-beall` |
| Connell's Children | `captain-felix`, `zephaniah-m-boyle`, `john-d-boyle-sr`, `john-boyle-jr`, `constantine-boyle`, `mary-boyle-1846`, `annie-boyle` |
| Captain Felix's Family | `mary-ann-oneill`, `paul-mary-boyle`, `nellie-carlin`, `felix-michael`, `robert-emmett-boyle` |
| Felix Michael's Family | `ida-ohara`, `charles-emmett-uncle`, `robert-lawrence` |

**Person fields:** id (text slug), name, altName, group, tags[], associatedPlaces[], born{year (TEXT), place}, died{year (TEXT), place}, parents[], spouse[], children[], siblings[], events[{year (TEXT), text}], notes

### Places (21 records in 5 groups)

| Group | Slugs |
|---|---|
| Monongahela River Sites | `romania-farm`, `lock-no-4` |
| Washington County | `carroll-township`, `boyle-family-cemetery`, `east-pike-run-distillery`, `fallowfield-township`, `beallsville`, `canonsburg`, `washington-pa`, `brownsville-fayette` |
| Pittsburgh & Allegheny County | `elizabethtown-pa`, `homestead`, `point-state-park`, `munhall`, `carnegie-tech`, `brehm-road` |
| Ireland | `killygordon-donegal` |
| Beyond Pennsylvania | `red-river-louisiana`, `national-military-home-dayton`, `thunder-bay-ontario`, `fort-belvoir-va` |

**Place fields:** id (text slug), name, altName, group, type, tags[], location{area, county, state, country}, established{year (TEXT), note}, status{year (TEXT), note}, currentStatus, associatedPeople[], relatedPlaces[], events[{year (TEXT), text}], notes

**Years are TEXT throughout — never coerce to integers.**

---

## Seed SQL strategy for `10l`

Build the seed in this order:

1. INSERT all 25 `seanchai.people` rows (slug, name, alt_name, person_group, born_year, born_place, died_year, died_place, notes) — use slug as the stable key
2. INSERT all 21 `seanchai.places` rows (slug, name, alt_name, place_group, place_type, loc_*, established_*, status_*, current_status, notes)
3. INSERT `seanchai.person_events` — join to people by slug via subselect
4. INSERT `seanchai.place_events` — join to places by slug via subselect
5. INSERT `seanchai.person_relationships` — join both slugs via subselect
6. INSERT `seanchai.person_place_assoc` — join both slugs via subselect
7. INSERT `seanchai.place_relations` — join both slugs via subselect
8. INSERT `seanchai.person_tags`
9. INSERT `seanchai.place_tags`

**Subselect pattern for slug resolution (use consistently):**

```sql
INSERT INTO seanchai.person_events (person_id, event_year, event_text, sort_order)
SELECT p.id, 'c. 1748', 'Born in County Donegal, Ireland', 1
FROM seanchai.people p WHERE p.slug = 'phelim-oboyle';
```

---

## Step 2 preview (not yet) — Curator Register tab

After step 1 is deployed:

- New tab "Register" on the Seanchaí crew dashboard (`/crew/seanchai`)
- Two JSON routes: `GET /crew/seanchai/register/people` and `.../places`
- `_register.html` partial: artifact's sidebar+panel HTML, unchanged in structure
- `register.js`: replaces hardcoded arrays with fetch calls; rest of the JS (search, filter, chips, timeline) ports over with minimal changes

---

## Commit message vocabulary

- `chart` — schema changes
- `trim` — polish
- `patch` — bug fix

---

## Hard constraints (never skip)

- All writes go to GitHub; Carolyn pulls on VPS — never edit VPS files directly
- `web_app_user` has EXECUTE-only on `api` schema — GRANT SELECT on tables is separate (done in `10k`)
- GRANT must be re-run after every new `api.*` function added in Step 3
- Test on scratch Postgres 16 before Carolyn runs anything live
- Years are TEXT throughout
- Do not touch the artifact until the Curator version matches it
