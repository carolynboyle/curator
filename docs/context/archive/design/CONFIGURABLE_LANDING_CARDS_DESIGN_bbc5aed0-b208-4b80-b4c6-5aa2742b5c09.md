# Design: Configurable Role-Based Landing Page Cards

**Date:** 2026-06-27  
**Status:** Concept / Future roadmap  
**Scope:** Architecture for making Curator a rebrandable, multi-business platform via configurable landing cards

---

## Vision

Curator is currently built for WCYJ's hardware refurbishment operation. But the underlying architecture — projects, contacts, organizations, role-based access — is generic enough to power **any small business operation**.

By making landing page cards configurable per role, Curator becomes a platform:

- **WCYJ Refurb Operation** — Captain sees "Refurb Projects" + "Identities" cards
- **WCYJ Store** (whycantyoujust.tech) — Store Manager sees "Store Inventory" + "Sales Orders" cards
- **Vendor Portal** — Vendor sees "My Listings" + "Sales Performance" cards
- **Small Business SaaS** — Accountant sees "Invoices" + "Clients", Manager sees "Projects" + "Team", etc.

Same Curator codebase. Different configurations.

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
