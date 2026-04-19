# form.html

**Path:** src/curator/templates/tasks/form.html
**Syntax:** html
**Generated:** 2026-04-19 14:58:02

```html
{% extends "base.html" %}
{% block title %}{% if task %}Edit Task{% else %}New Task{% endif %} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{% if task %}Edit Task{% else %}New Task{% endif %}</h1>
    <a href="{{ next }}" class="btn-secondary">Cancel</a>
</div>

<form method="post"
      action="{% if task %}/tasks/{{ task.id }}/edit{% else %}/tasks/new/{{ project.slug }}{% endif %}"
      class="curator-form">

    <input type="hidden" name="project_slug" value="{{ project.slug }}">
    <input type="hidden" name="next_url" value="{{ next }}">

    {% for field in view.fields %}

    {% if field.name == "description" %}
    <label for="description">
        {{ field.label }}{% if field.required %} *{% endif %}
        <textarea id="description"
                  name="description"
                  {% if field.required %}required{% endif %}
                  placeholder="{{ field.placeholder or '' }}">{{ task.description if task else '' }}</textarea>
    </label>

    {% elif field.name == "status_id" %}
    <label for="status_id">
        {{ field.label }}{% if field.required %} *{% endif %}
        <select id="status_id" name="status_id" {% if field.required %}required{% endif %}>
            <option value="">— select —</option>
            {% for opt in status_options %}
            <option value="{{ opt.id }}"
                {% if task and task.status_id == opt.id %}selected{% endif %}>
                {{ opt.display }} {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% elif field.name == "priority_id" %}
    <label for="priority_id">
        {{ field.label }}{% if field.required %} *{% endif %}
        <select id="priority_id" name="priority_id" {% if field.required %}required{% endif %}>
            <option value="">— select —</option>
            {% for opt in priority_options %}
            <option value="{{ opt.id }}"
                {% if task and task.priority_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% elif field.name == "parent_id" %}
    <label for="parent_id">
        {{ field.label }}
        <select id="parent_id" name="parent_id">
            <option value="">— none —</option>
            {% for opt in parent_options %}
            <option value="{{ opt.id }}"
                {% if task and task.parent_id == opt.id %}selected
                {% elif parent_id and parent_id == opt.id %}selected{% endif %}>
                {{ opt.description }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% elif field.name == "links" %}
    <label for="links">
        {{ field.label }}
        <input type="text"
               id="links"
               name="links"
               value="{{ task.links if task else '' }}"
               placeholder="{{ field.placeholder or '' }}">
        {% if field.help_text %}
        <small class="field-help">{{ field.help_text }}</small>
        {% endif %}
    </label>

    {% elif field.name == "notes" %}
    <label for="notes">
        {{ field.label }}
        <textarea id="notes"
                  name="notes"
                  placeholder="{{ field.placeholder or '' }}">{{ task.notes if task else '' }}</textarea>
        {% if field.help_text %}
        <small class="field-help">{{ field.help_text }}</small>
        {% endif %}
    </label>

    {% endif %}
    {% endfor %}

    <div class="form-actions">
        <button type="submit" class="btn-primary">
            {% if task %}Save Changes{% else %}Create Task{% endif %}
        </button>
        <a href="{{ next }}" class="btn-secondary">Cancel</a>
    </div>

</form>

{# Force delete confirmation — only shown when task has children #}
{% if task and task.child_count and task.child_count > 0 %}
<div class="confirm-delete" style="margin-top: 2rem;">
    <p><strong>This task has {{ task.child_count }} subtask(s).</strong>
    Deleting it will also delete all subtasks.</p>
    <form method="post" action="/tasks/{{ task.id }}/force-delete">
        <input type="hidden" name="project_slug" value="{{ project.slug }}">
        <input type="hidden" name="next_url" value="{{ next }}">
        <button type="submit" class="btn-danger">Delete Task and All Subtasks</button>
    </form>
</div>
{% endif %}

{% endblock %}

```
