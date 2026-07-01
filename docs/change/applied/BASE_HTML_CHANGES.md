# base.html — Add Tabulator CDN

Add these two lines immediately after the tabs.css link and before the Theme comment:

## BEFORE

```html
    <link rel="stylesheet" href="/static/css/components/tabs.css">
    <link rel="stylesheet" href="/static/css/components/datasheet.css">

    <!-- Theme -->
```

## AFTER

```html
    <link rel="stylesheet" href="/static/css/components/tabs.css">
    <link rel="stylesheet" href="/static/css/components/datasheet.css">

    <!-- Tabulator data grid -->
    <link rel="stylesheet" href="https://unpkg.com/tabulator-tables@6.5.0/dist/css/tabulator.min.css">

    <!-- Theme -->
```

And add the Tabulator JS just before the closing </body>, after the datasheet.js line:

## BEFORE

```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <!-- Datasheet engine -->
    <script src="/static/js/datasheet.js" defer></script>
</body>
```

## AFTER

```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <!-- Tabulator data grid -->
    <script src="https://unpkg.com/tabulator-tables@6.5.0/dist/js/tabulator.min.js"></script>
</body>
```

Note: datasheet.js is removed — Tabulator replaces it entirely.
