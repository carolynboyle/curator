# Design: Configurable Role-Based Landing Page Cards

**Date:** 2026-06-27  
**Status:** Concept / Future roadmap  
**Scope:** Architecture for making Curator a rebrandable, multi-business platform via configurable landing cards

---

## The Door Opens: Three "Speak Friend" Moments

Gandalf spent years mastering every spell, trying to force his way through the Doors of Durin. He exhausted every trick. Then he stepped back, looked at the door again, and saw what was written there: "Speak, Friend, and Enter." He spoke one word—"Friend"—and the doors opened.

Durin Observatory is built on that principle. No magical hand-waving. No forcing square tools into round problems.

### First "Speak Friend": Dr. Filewalker

You built a documentation generator package. Its job: syntax-highlight code and generate docs. Simple tool, one purpose.

Then you stepped back and realized: **this same structure can browse files**. The doc-gen's design — the way it walked the filesystem, rendered content — wasn't just for documentation. It was a file browser waiting to be discovered. Dr. Filewalker was born, not invented.

### Second "Speak Friend": Mermaid as UI, Manifests as Sensors

You wanted a graphical web UI for something. You had no idea how to build that.

So you documented the thing using Mermaid diagrams. You drew boxes and arrows to explain the architecture to yourself.

Then you looked at those diagrams and realized: **this is the UI**. Not a mockup of the UI. The actual UI. The simple answer was already there in your documentation. Mermaid became your visualization layer.

But there's more.

**Dr. Filewalker creates filesystem manifests** — snapshots of what files exist, their sizes, timestamps. Simple inventory.

Then you realized: **compare manifests over time, and you can see how the filesystem is changing**. Which directories grew? Which shrunk? Which are stable?

Then you realized: **those changes can color the nodes on your Mermaid chart**. A green star means "healthy, no change." Yellow means "growing." Red means "critical." Gray means "no data."

That's the **Observatory Star Map**. Not visualizing the system *architecture*. Visualizing the system *health*.

Started as storage capacity monitoring. One problem solved.

But the pattern is pure "Speak Friend" simplicity: **observe a system, track its changes, visualize the results**. That pattern works for:

- **Storage capacity** — green/yellow/red by disk usage
- **Warehouse inventory** — green/yellow/red by item counts
- **Outstanding documents** — green/yellow/red by esignature status
- **Project progress** — green/yellow/red by task completion
- **Vendor performance** — green/yellow/red by order fulfillment
- Anything that can be counted and compared over time

The Observatory isn't a dashboard. It's a **monitoring framework** built on one simple idea: manifest comparison → state change → visualization.

### Third "Speak Friend": Curator as the Platform

You had Filewalker (file browsing). You had visualization (Mermaid). You wanted to build a small business management platform.

You started building project management features. Contacts. Organizations. Role-based access.

Then you stepped back and realized: **Curator isn't a project management tool. It's the business data layer that ties everything together.** It's the door. It's the word "Friend."

You didn't invent a new platform. You recognized what was already possible. Curator becomes the configurable business logic engine. Filewalker browses files. Mermaid visualizes. Curator manages data. Together: Durin Observatory.

---

## Vision

Curator is currently built for WCYJ's hardware refurbishment operation. But the underlying architecture — projects, contacts, organizations, role-based access — is generic enough to power **any small business operation**.

By making landing page cards configurable per role, Curator becomes a platform for **any business** to configure its own workflows, roles, and data structures.

Alongside Curator, the **Observatory Star Map** provides monitoring and visualization:

- **Dr. Filewalker** creates filesystem manifests (snapshots of what exists)
- **Observatory** compares manifests over time to detect changes
- **Mermaid** visualizes the changes as a "star map" where each node's color reflects its current state
- **Curator** provides the business logic that determines what matters (inventory levels, document status, project progress, vendor performance)

Together, they form Durin Observatory: **simple tools that observe systems, detect changes, and visualize results**. No magical dashboards. Just manifest comparison, state tracking, and clear visualization.

---

## Core Concept: Landing Card Configuration

Instead of hardcoding "Captain sees Refurb Projects + Identities", the backend says:

> "User with role=captain in business=wcyj_refurb should see cards defined in role_config['captain']['landing_cards']"

Each card:
- Has a **title** and **subtitle** (user-facing labels)
- Points to a **route** (e.g., `/crew?role=captain` for projects)
- Has **optional specialized form** (e.g., Captain's Identities panel)
- Has **access control** (who can see this card)

---

## Architecture

### 1. Role & Business Configuration (Database)

New tables in `identity` schema:

```sql
-- identity.business
CREATE TABLE identity.business (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    config JSONB,  -- customizable settings
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- identity.role
CREATE TABLE identity.role (
    id BIGINT PRIMARY KEY,
    business_id BIGINT REFERENCES identity.business (id),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    permissions JSONB,  -- role capabilities
    UNIQUE(business_id, name)
);

-- identity.landing_card
CREATE TABLE identity.landing_card (
    id BIGINT PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES identity.role (id),
    title VARCHAR(255) NOT NULL,
    subtitle VARCHAR(255),
    route VARCHAR(500) NOT NULL,  -- e.g., "/crew?role=captain"
    icon VARCHAR(50),              -- CSS icon class or emoji
    color VARCHAR(50),             -- theme color variable
    form_type VARCHAR(50),         -- e.g., "identities", "inventory", null
    sort_order INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- identity.user_role (linking app_user to role)
CREATE TABLE identity.user_role (
    id BIGINT PRIMARY KEY,
    app_user_id BIGINT REFERENCES identity.app_user (id),
    role_id BIGINT REFERENCES identity.role (id),
    business_id BIGINT REFERENCES identity.business (id),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(app_user_id, role_id, business_id)
);
```

**Example data:**

```sql
-- WCYJ Refurb Business
INSERT INTO identity.business (id, name, slug)
VALUES (1, 'WCYJ Refurbishment', 'wcyj_refurb');

-- Captain role in WCYJ Refurb
INSERT INTO identity.role (id, business_id, name, display_name)
VALUES (1, 1, 'captain', 'Captain');

-- Landing cards for captain role
INSERT INTO identity.landing_card (role_id, title, subtitle, route, form_type, sort_order)
VALUES
  (1, 'Refurb Projects', 'Hardware inventory & projects', '/crew?role=captain', NULL, 1),
  (1, 'Identities', 'Contacts & organizations', '/crew?role=captain#identities', 'identities', 2);

-- WCYJ Store Business (future)
INSERT INTO identity.business (id, name, slug)
VALUES (2, 'Why Cant You Just Store', 'wcyj_store');

INSERT INTO identity.role (id, business_id, name, display_name)
VALUES (2, 2, 'store-manager', 'Store Manager');

INSERT INTO identity.landing_card (role_id, title, subtitle, route, form_type, sort_order)
VALUES
  (2, 'Store Inventory', 'Computer hardware for sale', '/store/inventory', 'store_inventory', 1),
  (2, 'Sales Orders', 'Customer orders & fulfillment', '/store/orders', 'store_orders', 2);
```

---

### 2. Backend: Query Landing Cards

New endpoint or template context:

```python
# crew.py

async def get_landing_cards(db: AsyncDBConnection, user_id: int, role_id: int):
    """Fetch landing cards configured for this user's role."""
    sql = """
        SELECT
            id,
            title,
            subtitle,
            route,
            icon,
            color,
            form_type,
            sort_order
        FROM identity.landing_card
        WHERE role_id = %s
          AND is_active = TRUE
        ORDER BY sort_order
    """
    cards = await db.fetch_all(sql, (role_id,))
    return [dict(row) for row in cards]

@router.get("/landing")
async def landing_page(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Landing page with role-specific cards."""
    user = get_current_user(request)  # from auth middleware
    
    landing_cards = await get_landing_cards(db, user.id, user.role_id)
    
    data = {
        "user": user,
        "cards": landing_cards,
    }
    template = env.get_template("landing.html")
    return HTMLResponse(template.render(**data))
```

---

### 3. Frontend: Generic Card Template

```html
<!-- landing.html -->

<div class="landing-cards">
  {% for card in cards %}
    <a href="{{ card.route }}" class="landing-card" data-form-type="{{ card.form_type }}">
      <div class="card-icon">
        {% if card.icon %}
          <i class="icon-{{ card.icon }}"></i>
        {% endif %}
      </div>
      <h2 class="card-title">{{ card.title }}</h2>
      <p class="card-subtitle">{{ card.subtitle }}</p>
      <div class="card-arrow">→</div>
    </a>
  {% endfor %}
</div>
```

---

### 4. Specialized Forms (Optional)

Some cards may need **custom panels** (like Captain's Identities tab):

```python
# In landing.html or a detail route
{% if card.form_type == "identities" %}
  {% include 'partials/_identities_panel.html' %}
{% elif card.form_type == "store_inventory" %}
  {% include 'partials/_inventory_panel.html' %}
{% elif card.form_type == "sales_orders" %}
  {% include 'partials/_orders_panel.html' %}
{% endif %}
```

The template is **generic** — it just says "if form_type is X, include the X partial". New businesses add new form_type values without touching the template.

---

## Benefits

### For WCYJ
- Captain panel works as-is
- Easy to add new roles (Scribe, Mechanic, Envoy) without code changes
- Identities panel moves from special captain.html to a configurable card

### For Vendors (Future)
- Vendor role sees their own inventory + performance cards
- Same projects/contacts infrastructure, different data access
- No need to build separate UI

### For Small Business SaaS
- Different business types (accounting, project management, team coordination) use same Curator UI
- Each business has its own roles, cards, and specialized forms
- Scale by adding businesses, not rewriting code

### For You
- Platform becomes **rebrandable** — whitelabel potential
- **Configurable by non-technical users** — Captain can add/reorder cards via UI (future)
- **Future-proof** — adding new business types doesn't require code changes

---

## Implementation Roadmap

### Phase 1 (Current)
- Implement what exists (projects grid, detail panels, identities)
- Keep captain.html and crew.html separate for now
- Note the refactor opportunity

### Phase 2 (Next)
- Create `identity.business` and `identity.role` tables
- Move hardcoded role names to database
- Add `identity.landing_card` table with seed data for WCYJ

### Phase 3 (Future)
- Create `/landing` endpoint that queries landing_card
- Build generic landing.html that renders cards from database
- Merge captain.html and crew.html into single template with conditional forms

### Phase 4 (Future)
- Captain's Command Center UI for managing roles and cards
- Add new vendor role with vendor-specific cards and permissions
- Test same Curator instance serving multiple businesses

---

## Example: Store Integration (Whitepaper)

Imagine Felipe wants to sell refurbished hardware through whycantyoujust.tech. Same Curator instance, different business configuration:

### WCYJ Refurb (Current)
```
Business: wcyj_refurb
Roles: captain, scribe, mechanic, envoy
Landing Cards:
  - Refurb Projects
  - Identities
  - (future) Quality Control
  - (future) Shipping
```

### WCYJ Store (Future)
```
Business: wcyj_store
Roles: store-manager, inventory-tech, sales
Landing Cards:
  - Store Inventory (reuses projects, different type)
  - Sales Orders (reuses projects for orders)
  - (future) Customer Reviews
  - (future) Pricing Rules
```

**Same Curator code.** Different businesses, roles, cards, and forms.

---

## Open Questions (Decide Later)

1. **Card customization UI** — Should Captain be able to reorder/hide cards via dashboard?
2. **Card-level permissions** — Can role X see card Y based on business rules?
3. **Dynamic forms** — Can Captain define custom form fields for identities without code?
4. **Multi-business users** — Can one user have roles in multiple businesses? (Yes, but requires sessions/context switching)
5. **Form type registry** — How do we keep track of all available form_type values? (Documentation? Database table?)

---

## Alignment with Core Values

✅ **No hardcoded values** — Roles, cards, and forms live in database  
✅ **Database-first design** — Landing cards configured in landing_card table  
✅ **Modular architecture** — Each form_type is a separate partial  
✅ **Rebrandable platform** — Same code, different businesses  
✅ **Captain Rule** — Captain manages roles and cards via UI (future)

---

## Next Steps

1. **Keep this doc** for reference and future roadmap
2. **Implement current work** (detail panels, fixing colors) without this in mind
3. **When merging captain.html + crew.html**, use this as the architecture guide
4. **When adding vendor role**, start building toward Phase 2 (database-driven roles and cards)

This is a long-term vision, not immediate work. But it shapes how you organize code and data going forward.
