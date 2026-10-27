# Change: Landing Page Cards

**Commit type:** `trim`  
**Commit message:** `trim: add configurable crew cards to landing page`

---

## Files changed

1. `src/curator/data/curator.yaml` — add `landing.cards` section
2. `src/curator/web/app.py` — pass cards to index template
3. `src/curator/templates/index.html` — render cards
4. `static/curator.css` — add card accent color classes

---

## 1. src/curator/data/curator.yaml

Add the following section at the end of the file.

### AFTER (append to file)

```yaml
landing:
  cards:
    - title: "The Captain"
      subtitle: "Full project management · All records"
      url: "/projects/board"
      color: "teal"
    - title: "The Scribe"
      subtitle: "Writing projects · Draft · Publish · Archive"
      url: "/projects/board?type=writing"
      color: "slate"
    - title: "The Mechanic"
      subtitle: "Hardware management · Refurb · Inventory"
      url: "/mechanic"
      color: "amber"
    - title: "The Envoy"
      subtitle: "Connections · Remote support · Network"
      url: "/envoy"
      color: "navy"
```

---

## 2. src/curator/web/app.py

### BEFORE

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
```

### AFTER

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    from curator.config import ConfigManager
    config = ConfigManager()
    cards = config.get_section("landing").get("cards", [])
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"cards": cards},
    )
```

---

## 3. src/curator/templates/index.html

### BEFORE

```html
{% extends "base.html" %}
{% block title %}The Curator{% endblock %}
{% block content %}
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 3rem 1rem;">
    <img src="/static/img/curator.png"
         alt="The Curator"
         style="max-width: 600px; width: 100%; margin-bottom: 2rem;">
    <a href="/projects/board" class="btn-primary" style="font-size: 1.1rem; padding: 0.75rem 2rem;">
        Go to Projects
    </a>
</div>
{% endblock %}
```

### AFTER

```html
{% extends "base.html" %}
{% block title %}The Curator{% endblock %}
{% block content %}
<div class="landing-page">
  <h1 class="landing-title">Project Crew</h1>
  <div class="landing-cards">
    {% for card in cards %}
    <a href="{{ card.url }}" class="landing-card landing-card--{{ card.color }}">
      <div class="landing-card-title">{{ card.title }}</div>
      <div class="landing-card-subtitle">{{ card.subtitle }}</div>
    </a>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

---

## 4. static/curator.css

Append the following at the end of the file.

### AFTER (append to file)

```css
/* -- Landing page --------------------------------------------------------- */

.landing-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem 1rem;
    gap: 2rem;
}

.landing-title {
    font-size: 2rem;
    color: var(--color-dark);
    letter-spacing: 0.04em;
    margin: 0;
}

.landing-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    width: 100%;
    max-width: 800px;
}

.landing-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 2.5rem 1.5rem;
    border-radius: 8px;
    text-decoration: none;
    transition: transform 0.15s, box-shadow 0.15s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.10);
    min-height: 160px;
}

.landing-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}

.landing-card-title {
    font-size: 1.3rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    margin-bottom: 0.5rem;
}

.landing-card-subtitle {
    font-size: 0.9rem;
    opacity: 0.85;
}

/* Card color variants */

.landing-card--teal {
    background-color: var(--color-teal);
    color: #ffffff;
}

.landing-card--slate {
    background-color: #475569;
    color: #ffffff;
}

.landing-card--amber {
    background-color: #b45309;
    color: #ffffff;
}

.landing-card--navy {
    background-color: #1e3a5f;
    color: #ffffff;
}
```
