# views.yaml

**Path:** src/curator/data/views.yaml
**Syntax:** yaml
**Generated:** 2026-04-16 11:00:26

```yaml
# curator views.yaml - View definitions for the projects database.
#
# This is the reference implementation for the projects database schema.
# To use the Curator with a different database, replace this file with
# your own view definitions. See the README for viewkit's format documentation.
#
# Each top-level key is a view name passed to ViewBuilder.get_view().
# columns: define the list/table view for that resource.
# fields:  define the create/edit form for that resource.
#
# Field types: text, textarea, select, date, number, checkbox
# Select fields require a 'source' naming the lookup table or data source.
# The Curator's repository layer is responsible for fetching select options.

projects:
  title: "Projects"
  columns:
    - name: name
      label: "Project"
      link: true
      sortable: true
    - name: status
      label: "Status"
      sortable: true
    - name: project_type
      label: "Type"
      sortable: true
    - name: parent_name
      label: "Parent"
    - name: open_tasks
      label: "Open"
    - name: total_tasks
      label: "Total"
  fields:
    - name: name
      label: "Name"
      type: text
      required: true
      placeholder: "My Project"
    - name: slug
      label: "Slug"
      type: text
      required: true
      readonly: true
      help_text: "Auto-generated from name. Not editable after creation."
    - name: description
      label: "Description"
      type: textarea
    - name: status_id
      label: "Status"
      type: select
      source: project_status
      required: true
    - name: type_id
      label: "Type"
      type: select
      source: project_type
    - name: parent_id
      label: "Parent Project"
      type: select
      source: projects
    - name: target_date
      label: "Target Date"
      type: date

tasks:
  title: "Tasks"
  columns:
    - name: description
      label: "Task"
      link: true
    - name: status_display
      label: "Status"
    - name: priority
      label: "Priority"
      sortable: true
    - name: project_name
      label: "Project"
  fields:
    - name: description
      label: "Description"
      type: textarea
      required: true
    - name: status_id
      label: "Status"
      type: select
      source: task_status
      required: true
    - name: priority_id
      label: "Priority"
      type: select
      source: priority
      required: true
    - name: parent_id
      label: "Parent Task"
      type: select
      source: tasks
    - name: links
      label: "Links"
      type: text
      placeholder: "Comma-separated URLs"
      help_text: "Optional links related to this task."

tags:
  title: "Tags"
  columns:
    - name: name
      label: "Tag"
      link: true
      sortable: true
    - name: category
      label: "Category"
      sortable: true
  fields:
    - name: name
      label: "Name"
      type: text
      required: true
    - name: category_id
      label: "Category"
      type: select
      source: tag_category

files:
  title: "Files"
  columns:
    - name: label
      label: "Label"
      link: true
    - name: file_type
      label: "Type"
    - name: location_type
      label: "Location Type"
    - name: location
      label: "Location"
      truncate: 60
  fields:
    - name: label
      label: "Label"
      type: text
      required: true
      placeholder: "source repo"
    - name: file_type_id
      label: "File Type"
      type: select
      source: file_type
      required: true
    - name: location
      label: "Location"
      type: text
      required: true
      placeholder: "https://github.com/... or /path/to/file"
    - name: location_type_id
      label: "Location Type"
      type: select
      source: location_type
      required: true
    - name: notes
      label: "Notes"
      type: textarea
```
