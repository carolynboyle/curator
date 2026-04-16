# index.html

**Path:** src/curator/templates/index.html
**Syntax:** html
**Generated:** 2026-04-16 11:00:26

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
