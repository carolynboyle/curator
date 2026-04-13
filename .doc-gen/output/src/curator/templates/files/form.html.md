# form.html

**Path:** src/curator/templates/files/form.html
**Syntax:** html
**Generated:** 2026-04-12 14:34:39

```html
{% extends "base.html" %}
{% block title %}{% if file %}Edit File{% else %}New File{% endif %} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{% if file %}Edit File{% else %}New File{% endif %}</h1>
    <a href="{% if project_slug %}/projects/{{ project_slug }}{% else %}/projects/{% endif %}"
       class="btn-secondary">Cancel</a>
</div>

<form method="post"
      action="{% if file %}/files/{{ file.id }}/edit{% else %}/files/new{% endif %}"
      class="curator-form">

    {# Pass context back through the form so we can redirect correctly #}
    <input type="hidden" name="project_id" value="{{ project_id or '' }}">
    <input type="hidden" name="task_id" value="{{ task_id or '' }}">
    <input type="hidden" name="project_slug" value="{{ project_slug or '' }}">

    {% for field in view.fields %}

    {% if field.name == "label" %}
    <label for="label">
        {{ field.label }}{% if field.required %} *{% endif %}
        <input type="text"
               id="label"
               name="label"
               value="{{ file.label if file else '' }}"
               {% if field.required %}required{% endif %}
               placeholder="{{ field.placeholder or '' }}">
    </label>

    {% elif field.name == "file_type_id" %}
    <label for="file_type_id">
        {{ field.label }}{% if field.required %} *{% endif %}
        <select id="file_type_id" name="file_type_id" {% if field.required %}required{% endif %}>
            <option value="">— select —</option>
            {% for opt in file_type_options %}
            <option value="{{ opt.id }}"
                {% if file and file.file_type_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% elif field.name == "location" %}
    <label for="location">
        {{ field.label }}{% if field.required %} *{% endif %}
        <input type="text"
               id="location"
               name="location"
               value="{{ file.location if file else '' }}"
               {% if field.required %}required{% endif %}
               placeholder="{{ field.placeholder or '' }}">
    </label>

    {% elif field.name == "location_type_id" %}
    <label for="location_type_id">
        {{ field.label }}{% if field.required %} *{% endif %}
        <select id="location_type_id" name="location_type_id" {% if field.required %}required{% endif %}>
            <option value="">— select —</option>
            {% for opt in location_type_options %}
            <option value="{{ opt.id }}"
                {% if file and file.location_type_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% elif field.name == "notes" %}
    <label for="notes">
        {{ field.label }}
        <textarea id="notes"
                  name="notes"
                  placeholder="{{ field.placeholder or '' }}">{{ file.notes if file else '' }}</textarea>
        {% if field.help_text %}
        <small class="field-help">{{ field.help_text }}</small>
        {% endif %}
    </label>

    {% endif %}
    {% endfor %}

    <div class="form-actions">
        <button type="submit" class="btn-primary">
            {% if file %}Save Changes{% else %}Add File{% endif %}
        </button>
        <a href="{% if project_slug %}/projects/{{ project_slug }}{% else %}/projects/{% endif %}"
           class="btn-secondary">Cancel</a>
    </div>

</form>
{% endblock %}
```
