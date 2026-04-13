# curator.yaml

**Path:** src/curator/data/curator.yaml
**Syntax:** yaml
**Generated:** 2026-04-12 14:34:39

```yaml
# curator.yaml - Curator default configuration
#
# This file ships with the Curator and provides defaults.
# To override, create ~/.config/curator/curator.yaml with only
# the keys you want to change. You do not need to repeat keys
# that match the defaults.
#
# The database connection is configured separately in
# ~/.config/dev-utils/config.yaml under the 'dbkit:' key.
# Passwords are handled by ~/.pgpass — never put credentials here.

app:
  name: "The Curator"
  version: "0.1.0"

server:
  host: "127.0.0.1"      # Override with Tailscale IP in production
  port: 8080

ui:
  page_size: 25           # Rows per page in list views
  date_format: "%Y-%m-%d"

plugin:
  name: "The Curator"
  version: "0.1.0"
  description: "Web UI and database interface for the projects database"
  type: "web"
  crew_member: "curator"
```
