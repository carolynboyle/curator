# Change: Restore Curator Image and Single-Row Cards

**Commit type:** `trim`  
**Commit message:** `trim: restore curator image and single-row card layout on landing page`

---

## Files changed

1. `src/curator/templates/index.html` — add curator image above cards
2. `static/curator.css` — single-row cards, smaller size

---

## 1. src/curator/templates/index.html

### BEFORE

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

### AFTER

```html
{% extends "base.html" %}
{% block title %}The Curator{% endblock %}
{% block content %}
<div class="landing-page">
  <img src="/static/img/curator.png"
       alt="The Curator"
       class="landing-hero-img">
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

**Why:** Adds the curator image back above the cards. The `<h1>` title has been removed since the image serves as the page header. A dedicated `landing-hero-img` class keeps the image styling in CSS where it belongs.

---

## 2. static/curator.css

### BEFORE

```css
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
```

### AFTER

```css
.landing-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem 1rem;
    gap: 1.5rem;
}

.landing-hero-img {
    max-width: 480px;
    width: 100%;
}

.landing-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    width: 100%;
    max-width: 960px;
}

.landing-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 1.25rem 1rem;
    border-radius: 8px;
    text-decoration: none;
    transition: transform 0.15s, box-shadow 0.15s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.10);
    min-height: 100px;
}
```

**Why:**
- `.landing-page` gap reduced slightly since the image is doing more visual work than the old title
- `.landing-hero-img` is a new rule; `max-width: 480px` keeps the image prominent without dominating the full viewport width
- `.landing-cards` changes from `repeat(2, 1fr)` to `repeat(4, 1fr)` so all four cards sit in one row; `max-width` widened to 960px to give the row breathing room
- `.landing-card` padding reduced from `2.5rem 1.5rem` to `1.25rem 1rem` and `min-height` from `160px` to `100px` so cards are compact beneath the image

---

## Note on the removed `.landing-title` rule

The `.landing-title` CSS class can be left in the file — it's harmless with no element using it. Remove it in a future cleanup pass if you like.
