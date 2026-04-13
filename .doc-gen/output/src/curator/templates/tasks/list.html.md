# list.html

**Path:** src/curator/templates/tasks/list.html
**Syntax:** html
**Generated:** 2026-04-13 04:51:40

```html
{% extends "base.html" %}
{% block title %}Tasks — {{ project.name }} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{{ project.name }} — Tasks</h1>
    <div>
        <a href="/projects/{{ project.slug }}" class="btn-secondary">Back to Project</a>
        <a href="/tasks/new/{{ project.slug }}" class="btn-primary">New Task</a>
    </div>
</div>

{% if tasks %}
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
<div class="empty-state">
    No tasks yet. <a href="/tasks/new/{{ project.slug }}">Add one.</a>
</div>
{% endif %}
{% endblock %}
```
