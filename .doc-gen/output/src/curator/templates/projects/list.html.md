# list.html

**Path:** src/curator/templates/projects/list.html
**Syntax:** html
**Generated:** 2026-04-19 14:58:02

```html
{% extends "base.html" %}
{% block title %}Projects — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{{ view.title }}</h1>
    <a href="/projects/new" class="btn-primary">New Project</a>
</div>

<div style="margin-bottom: 1rem;">
    <a href="/projects/" class="btn-secondary btn-sm {% if not active_status %}active{% endif %}">All</a>
    {% for opt in status_options %}
    <a href="/projects/?status={{ opt.name }}"
       class="btn-secondary btn-sm {% if active_status == opt.name %}active{% endif %}">
        {{ opt.name | capitalize }}
    </a>
    {% endfor %}
</div>

{% if projects %}
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
        {% for project in projects %}
        <tr>
            <td>
                {% if project.parent_name %}
                <small class="field-help">{{ project.parent_name }} /</small><br>
                {% endif %}
                <a href="/projects/{{ project.slug }}">{{ project.name }}</a>
            </td>
            <td>{{ project.status }}</td>
            <td>{{ project.project_type or "—" }}</td>
            <td>{{ project.parent_name or "—" }}</td>
            <td>{{ project.open_tasks }}</td>
            <td>{{ project.total_tasks }}</td>
            <td>
                <a href="/projects/{{ project.slug }}/edit" class="btn-secondary btn-sm">Edit</a>
                <form method="post" action="/projects/{{ project.slug }}/delete"
                      style="display:inline"
                      onsubmit="return confirm('Delete project {{ project.name }}?')">
                    <button type="submit" class="btn-danger btn-sm">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">No projects yet. <a href="/projects/new">Create one.</a></div>
{% endif %}
{% endblock %}

```
