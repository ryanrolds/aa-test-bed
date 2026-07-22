# aa-wanderer

Alliance Auth integration for the [Wanderer](https://github.com/wanderer-industries/wanderer)
EVE Online mapping tool.

This is the first plugin developed in the `wanderer-aa` test bed. It is installed
into the Alliance Auth container in editable mode and its source is bind-mounted,
so edits take effect on a container restart (no image rebuild required).

## Current state

Skeleton only: registers a **Wanderer** sidebar menu item, a `basic_access`
permission, and a placeholder page. The actual Wanderer integration logic is the
next milestone.

## Layout

```
wanderer/
  apps.py         AppConfig
  auth_hooks.py   menu item + url hook registration
  urls.py         url routes (app_name = "wanderer")
  views.py        views (permission-gated)
  models.py       General model carrying the basic_access permission
  migrations/     registers the permission
  templates/      Bootstrap-5 page templates
```
