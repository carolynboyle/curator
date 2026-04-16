# form.html

**Path:** src/curator/templates/tags/form.html
**Syntax:** html
**Generated:** 2026-04-16 11:00:26

```html
{% extends "base.html" %}
{% block title %}{% if tag %}Edit Tag{% else %}New Tag{% endif %} — The Curator{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{% if tag %}Edit Tag{% else %}New Tag{% endif %}</h1>
    <a href="/tags/" class="btn-secondary">Cancel</a>
</div>

<form method="post"
      action="{% if tag %}/tags/{{ tag.id }}/edit{% else %}/tags/new{% endif %}"
      class="curator-form">

    {% for field in view.fields %}

    {% if field.name == "name" %}
    <label for="name">
        {{ field.label }}{% if field.required %} *{% endif %}
        <input type="text"
               id="name"
               name="name"
               value="{{ tag.name if tag else '' }}"
               {% if field.required %}required{% endif %}
               placeholder="{{ field.placeholder or '' }}">
    </label>

    {% elif field.name == "category_id" %}
    <label for="category_id">
        {{ field.label }}
        <select id="category_id" name="category_id">
            <option value="">— none —</option>
            {% for opt in category_options %}
            <option value="{{ opt.id }}"
                {% if tag and tag.category_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
            {% endfor %}
        </select>
    </label>

    {% endif %}
    {% endfor %}

    <div class="form-actions">
        <button type="submit" class="btn-primary">
            {% if tag %}Save Changes{% else %}Create Tag{% endif %}
        </button>
        <a href="/tags/" class="btn-secondary">Cancel</a>
    </div>

</form>
{% endblock %}
```
