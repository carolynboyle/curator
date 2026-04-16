# list.html

**Path:** src/curator/templates/files/list.html
**Syntax:** html
**Generated:** 2026-04-16 11:00:26

```html
{% extends "base.html" %}
{% block title %}Files — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Files</h1>
</div>

{% if files %}
<table class="curator-table">
    <thead>
        <tr>
            <th>Label</th>
            <th>Type</th>
            <th>Location Type</th>
            <th>Location</th>
            <th>Project</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for file in files %}
        <tr>
            <td>{{ file.label }}</td>
            <td>{{ file.file_type }}</td>
            <td>{{ file.location_type }}</td>
            <td>
                {% if file.location_type in ('url', 'git', 's3') %}
                <a href="{{ file.location }}" target="_blank"
                   class="export-link">{{ file.location }}</a>
                {% else %}
                <span class="copyable-path"
                      onclick="navigator.clipboard.writeText('{{ file.location }}')"
                      title="Click to copy path"
                      style="cursor:pointer;">
                    📋 {{ file.location }}
                </span>
                {% endif %}
            </td>
            <td>
                {% if file.project_slug %}
                <a href="/projects/{{ file.project_slug }}">{{ file.project_name }}</a>
                {% else %}
                —
                {% endif %}
            </td>
            <td>
                <a href="/files/{{ file.id }}/edit"
                   class="btn-secondary btn-sm">Edit</a>
                <form method="post" action="/files/{{ file.id }}/delete"
                      style="display:inline"
                      onsubmit="return confirm('Delete this file record?')">
                    <input type="hidden" name="project_slug"
                           value="{{ file.project_slug or '' }}">
                    <button type="submit" class="btn-danger btn-sm">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">No file records yet.</div>
{% endif %}

{% endblock %}
```
