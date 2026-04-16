# board.html

**Path:** src/curator/templates/projects/board.html
**Syntax:** html
**Generated:** 2026-04-16 11:00:26

```html
{% extends "base.html" %}
{% block title %}Projects — The Curator{% endblock %}

{% block content %}
<div class="board-layout">

  {# ---- Left panel: project tree ---- #}
  <div class="board-left">
    <div class="board-left-header">
      <span>Projects</span>
      <a href="/projects/new" class="board-add-btn" title="New project">+</a>
    </div>
    <div class="board-list" id="board-list">
      {% for row in tree %}
        {% if row.depth == 0 %}
          {# Check if this project has children #}
          {% set ns = namespace(has_children=false) %}
          {% for other in tree %}
            {% if other.depth > 0 and other.path[0] == row.slug %}
              {% set ns.has_children = true %}
            {% endif %}
          {% endfor %}

          <div
            class="board-list-item"
            style="padding-left: 12px;"
            hx-get="/projects/{{ row.slug }}/panel"
            hx-target="#board-detail"
            hx-swap="innerHTML"
            hx-trigger="dblclick"
            onclick="boardSelect(this)"
            title="Double-click to open"
            data-slug="{{ row.slug }}"
          >
            {% if ns.has_children %}
              <span class="board-toggle" onclick="toggleChildren(event, '{{ row.slug }}')">▾</span>
            {% else %}
              <span class="board-toggle-spacer"></span>
            {% endif %}
            <span class="board-item-dot"></span>
            <span class="board-item-name">{{ row.name }}</span>
          </div>

        {% else %}
          <div
            class="board-list-item board-list-child"
            style="padding-left: 12px;"
            hx-get="/projects/{{ row.slug }}/panel"
            hx-target="#board-detail"
            hx-swap="innerHTML"
            hx-trigger="dblclick"
            onclick="boardSelect(this)"
            title="Double-click to open"
            data-parent="{{ row.path[0] }}"
          >
            <span class="board-indent-marker">└</span>
            <span class="board-item-dot"></span>
            <span class="board-item-name">{{ row.name }}</span>
          </div>
        {% endif %}
      {% endfor %}
    </div>
  </div>

  {# ---- Right panel: detail (starts empty) ---- #}
  <div class="board-right">
    <div id="board-detail" class="board-detail">
      <div class="board-empty">
        Double-click a project to open it.
      </div>
    </div>
  </div>

</div>

<script>
function boardSelect(el) {
    document.querySelectorAll('.board-list-item').forEach(function(i) {
        i.classList.remove('board-list-item--active');
    });
    el.classList.add('board-list-item--active');
}

function toggleChildren(event, slug) {
    event.stopPropagation();
    var toggle = event.target;
    var children = document.querySelectorAll('[data-parent="' + slug + '"]');
    var collapsed = toggle.textContent === '▶';

    if (collapsed) {
        toggle.textContent = '▾';
        children.forEach(function(c) { c.style.display = ''; });
    } else {
        toggle.textContent = '▶';
        children.forEach(function(c) { c.style.display = 'none'; });
    }
}
</script>
{% endblock %}
```
