# list.html

**Path:** src/curator/templates/tags/list.html
**Syntax:** html
**Generated:** 2026-04-16 11:00:26

```html
{% extends "base.html" %}
{% block title %}Tags — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{{ view.title }}</h1>
    <a href="/tags/new" class="btn-primary">New Tag</a>
</div>

{% if tags %}
<table class="curator-table">
    <thead>
        <tr>
            {% for col in view.columns %}
            <th>{{ col.label }}</th>
            {% endfor %}
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for tag in tags %}
        <tr>
            <td>{{ tag.name }}</td>
            <td>{{ tag.category or "—" }}</td>
            <td>
                <a href="/tags/{{ tag.id }}/edit" class="btn-secondary btn-sm">Edit</a>
                <form method="post" action="/tags/{{ tag.id }}/delete"
                      style="display:inline"
                      onsubmit="return confirm('Delete tag {{ tag.name }}?')">
                    <button type="submit" class="btn-danger btn-sm">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">No tags yet. <a href="/tags/new">Add one.</a></div>
{% endif %}
{% endblock %}

```
