# detail.html

**Path:** src/curator/templates/projects/detail.html
**Syntax:** html
**Generated:** 2026-04-19 14:58:02

```html
{% extends "base.html" %}
{% block title %}{{ project.name }} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>
        {% if project.parent_name %}
        <small class="field-help"><a href="/projects/{{ project.parent_slug }}">{{ project.parent_name }}</a> /</small><br>
        {% endif %}
        {{ project.name }}
    </h1>
    <div>
        <a href="/projects/{{ project.slug }}/edit" class="btn-secondary">Edit</a>
        <a href="/tasks/new/{{ project.slug }}" class="btn-primary">New Task</a>
    </div>
</div>

<div class="curator-card">
    <h3>Details</h3>
    <p><strong>Status:</strong> {{ project.status }}</p>
    <p><strong>Type:</strong> {{ project.project_type or "—" }}</p>
    {% if project.target_date %}
    <p><strong>Target Date:</strong> {{ project.target_date }}</p>
    {% endif %}
    {% if project.description %}
    <p>{{ project.description }}</p>
    {% endif %}
</div>

{# Tags #}
<div class="section-header">
    <h2>Tags</h2>
</div>
{% if tags %}
<div style="margin-bottom: 1rem;">
    {% for tag in tags %}
    <span class="badge badge-open">{{ tag.name }}</span>
    {% endfor %}
</div>
{% else %}
<div class="empty-state">No tags.</div>
{% endif %}

{# Subprojects #}
{% if subprojects %}
<div class="section-header">
    <h2>Subprojects</h2>
</div>
<table class="curator-table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Open</th>
            <th>Total</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for sub in subprojects %}
        <tr>
            <td><a href="/projects/{{ sub.slug }}">{{ sub.name }}</a></td>
            <td>{{ sub.status }}</td>
            <td>{{ sub.open_tasks }}</td>
            <td>{{ sub.total_tasks }}</td>
            <td>
                <a href="/projects/{{ sub.slug }}/edit" class="btn-secondary btn-sm">Edit</a>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}

{# Tasks #}
<div class="section-header">
    <h2>Tasks</h2>
    <a href="/tasks/new/{{ project.slug }}" class="btn-primary btn-sm">New Task</a>
</div>

{# Delete blocked warning #}
{% if request.query_params.get('delete_blocked') %}
<div class="confirm-delete">
    <p><strong>This task has {{ request.query_params.get('count') }} subtask(s).</strong>
    Delete subtasks first, or use force delete.</p>
</div>
{% endif %}

{% if tasks %}
<table class="curator-table">
    <thead>
        <tr>
            {% for col in task_view.columns %}
            <th>{{ col.label }}</th>
            {% endfor %}
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for task in tasks %}
        <tr>
            <td>
                <span class="task-depth-{{ task.depth }}">
                    {% if task.depth > 0 %}
                    <span class="task-indent-marker">↳</span>
                    {% endif %}
                    {{ task.description }}
                </span>
            </td>
            <td>
                <span class="badge
                    {% if task.status == 'open' %}badge-open
                    {% elif task.status == 'in progress' %}badge-progress
                    {% elif task.status == 'on hold' %}badge-hold
                    {% elif task.status == 'complete' %}badge-complete
                    {% endif %}">
                    {{ task.status }}
                </span>
            </td>
            <td>{{ task.priority }}</td>
            <td>{{ task.project_name }}</td>
            <td>
                <a href="/tasks/{{ task.id }}/edit" class="btn-secondary btn-sm">Edit</a>
                <form method="post" action="/tasks/{{ task.id }}/delete"
                      style="display:inline"
                      onsubmit="return confirm('Delete this task?')">
                    <input type="hidden" name="project_slug" value="{{ project.slug }}">
                    <button type="submit" class="btn-danger btn-sm">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">No tasks yet. <a href="/tasks/new/{{ project.slug }}">Add one.</a></div>
{% endif %}

{# Files #}
<div class="section-header">
    <h2>Files</h2>
    <a href="/files/new?project_id={{ project.id }}" class="btn-primary btn-sm">Add File</a>
</div>
{% if files %}
<table class="curator-table">
    <thead>
        <tr>
            <th>Label</th>
            <th>Type</th>
            <th>Location</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
        {% for file in files %}
        <tr>
            <td>{{ file.label }}</td>
            <td>{{ file.file_type }}</td>
            <td>
                {% if file.location_type in ('url', 'git', 's3') %}
                <a href="{{ file.location }}" target="_blank" class="export-link">{{ file.location }}</a>
                {% else %}
                <span class="copyable-path"
                      onclick="navigator.clipboard.writeText('{{ file.location }}')"
                      title="Click to copy"
                      style="cursor:pointer;">📋 {{ file.location }}</span>
                {% endif %}
            </td>
            <td>
                <a href="/files/{{ file.id }}/edit" class="btn-secondary btn-sm">Edit</a>
                <form method="post" action="/files/{{ file.id }}/delete"
                      style="display:inline"
                      onsubmit="return confirm('Delete this file record?')">
                    <input type="hidden" name="project_slug" value="{{ project.slug }}">
                    <button type="submit" class="btn-danger btn-sm">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">No files attached.</div>
{% endif %}

{# Danger zone #}
<div class="section-header" style="margin-top: 3rem;">
    <h2 style="color: var(--color-danger);">Danger Zone</h2>
</div>
<div class="confirm-delete">
    <p>Deleting this project will also delete all its tasks. Subprojects will be detached.</p>
    <form method="post" action="/projects/{{ project.slug }}/delete"
          onsubmit="return confirm('Permanently delete {{ project.name }} and all its tasks?')">
        <button type="submit" class="btn-danger">Delete Project</button>
    </form>
</div>

{% endblock %}

```
