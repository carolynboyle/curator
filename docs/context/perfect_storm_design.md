# Perfect Storm — Design Document

**Log Analysis System for Homelab Infrastructure**  
*Generated July 2026*

**Status:** Design only. Assumes Fascism Index tool-calling infrastructure
(`tool_agent.py`, `ToolRegistry`, `run_agent_turn()`) already exists and
is reusable without modification.

---

## 1. Name and Origin

"Perfect Storm" refers to the incident that motivated this system: a
T490 running Proxmox with a known buggy ethernet adapter (r8169 driver)
that had been generating error messages every ~2 seconds for 50+ minutes.
A new logout script — written to bypass Cinnamon desktop session handling
in an LMDE VM over xrdp — added just enough additional kernel/session
stress to push the system over the edge into full network loss.

The system was already at the margin. The script was the final stressor.
Had the logs been checked first, the script would not have been run until
the driver issue was resolved (which turned out to require only replacing
the ethernet cable).

Perfect Storm is the system that catches this class of problem before it
becomes an incident.

---

## 2. Core Problem

Static log monitors count errors. Perfect Storm reasons about them.

The distinction matters because:
- Frequency alone doesn't indicate risk (some errors are always present
  and harmless)
- Cascading failures involve correlated errors across subsystems, not
  just one error type spiking
- Risk is context-dependent: the same log state may be safe to proceed
  through under normal conditions but dangerous when a new script is
  about to add system stress
- A human checking logs manually has to know what to look for; Perfect
  Storm brings that knowledge to the check automatically

---

## 3. Curator Integration

### 3.1 The Task Type Mechanism

Curator's `tasks` table references a `task_status` lookup table
(id, name, sort_order). A parallel `task_type` lookup table does not
currently exist but is the natural extension point.

**Required database addition:**

```sql
CREATE TABLE task_type (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    sort_order INT         NOT NULL DEFAULT 0
);

-- Seed values (initial):
INSERT INTO task_type (name, sort_order) VALUES
    ('standard',      0),
    ('experimental',  10);  -- triggers Perfect Storm preflight check
```

`tasks` gains a nullable FK:

```sql
ALTER TABLE tasks
    ADD COLUMN type_id BIGINT REFERENCES task_type(id);
```

A task with `type_id` pointing to `experimental` is a task that requires
a log preflight check before its associated script is run.

### 3.2 The "Run Script" Button

A planned Curator UI feature: a button on the task detail panel that
executes the script associated with a task. The `source_file` column
on `tasks` (currently used to record which markdown/json file a task
originated from) is the candidate field for storing the script path,
or a new `script_path` column could be added.

When the button is clicked for an `experimental` task:
1. Curator's FastAPI backend receives the request
2. Backend calls `api.get_task_detail(task_id)` to confirm task type
3. If `type_id = experimental`: Perfect Storm preflight runs first
4. Perfect Storm returns a structured result (pass/warn/block)
5. If pass or warn-with-override: script executes
6. If block: script does not execute; result surfaces in Curator UI
   and writes to `messages.messages` via `api.create_message()`

**This is a planned feature, not yet built.** The design establishes
what Curator needs to support it; actual implementation is deferred.

### 3.3 Curator's API Boundary

Consistent with Curator's architecture: `web_app_user` has EXECUTE on
`api.*` only. Perfect Storm never touches tables directly. The relevant
API functions needed (some new, some may already exist):

```sql
-- Already exists (or equivalent):
api.get_task_detail(task_id BIGINT)

-- New, needed for Perfect Storm:
api.get_task_type(task_id BIGINT)          -- returns type name
api.create_message(...)                     -- already designed, not yet built
api.log_preflight_result(                   -- new
    task_id BIGINT,
    result TEXT,                            -- 'pass' | 'warn' | 'block'
    summary TEXT,
    detail JSONB
)
```

`api.log_preflight_result()` writes to a new table (see section 5).

---

## 4. Architecture

```
Curator UI (task detail panel)
        │
        │ "Run Script" button clicked
        ▼
Curator FastAPI backend
        │
        │ task type = 'experimental'?
        ▼
Perfect Storm Python service
        │
        ├─── Python: collect & preprocess logs
        │         (journalctl, configurable sources)
        │
        ├─── Python: frequency analysis, correlation, windowing
        │         (statistical summary — NOT sent to LLM raw)
        │
        ├─── Qwen (via llama.cpp / llama-server)
        │         receives: structured summary + script description
        │         may call: web_search, fetch_url, query_db tools
        │         returns: assessment + recommendation
        │
        └─── Result: pass / warn / block + explanation
                │
                ├─── api.log_preflight_result() → PostgreSQL
                ├─── api.create_message() → messages schema (if warn/block)
                └─── Response to Curator UI
```

### 4.1 Why Python Does the Heavy Lifting First

Qwen 7B has a context window of 32k tokens (with llama.cpp `-c 32768`).
Raw log files from a busy system can exceed this in minutes. More
importantly, the LLM doesn't need to see every line — it needs a
structured picture of:
- What's happening
- How often
- Whether things are getting worse
- What's correlated with what

Python generates that picture. Qwen interprets it.

### 4.2 Tool-Calling Reuse

Perfect Storm imports `tool_agent.py` from the Fascism Index project
unchanged. New tools are registered; the orchestration loop is identical.

```python
# perfect_storm.py
from tool_agent import ToolRegistry, run_agent_turn

# New tools for this project:
registry = ToolRegistry()
registry.register(schema_parse_logs,      parse_system_logs)
registry.register(schema_check_resources, check_system_resources)
registry.register(schema_known_issues,    query_known_hardware_issues)
registry.register(schema_search,          web_search)  # same as Fascism Index
```

---

## 5. Data Model

### 5.1 New PostgreSQL Tables

```sql
-- Log sources: configurable per host, consistent with Curator's
-- config-driven design philosophy.
CREATE TABLE infrastructure.log_source (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host        VARCHAR(100) NOT NULL,         -- 't490', 'wcyj-meet', etc.
    source_type VARCHAR(50)  NOT NULL,         -- 'journalctl', 'file', 'syslog'
    path        TEXT,                          -- for file sources
    unit_filter TEXT,                          -- for journalctl: --unit filter
    enabled     BOOLEAN      NOT NULL DEFAULT TRUE,
    notes       TEXT
);

-- Preflight check results
CREATE TABLE infrastructure.preflight_result (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id         BIGINT       NOT NULL REFERENCES tasks(id),
    checked_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    result          VARCHAR(10)  NOT NULL CHECK (result IN ('pass','warn','block')),
    summary         TEXT         NOT NULL,     -- plain English for Curator UI
    detail          JSONB,                     -- full structured output
    log_window_mins INT          NOT NULL,     -- how many minutes of logs scanned
    model_used      VARCHAR(100),              -- qwen3-8b, etc.
    script_executed BOOLEAN      NOT NULL DEFAULT FALSE,  -- did they proceed?
    executed_at     TIMESTAMPTZ               -- if they did
);

CREATE INDEX idx_preflight_task ON infrastructure.preflight_result(task_id);
CREATE INDEX idx_preflight_result ON infrastructure.preflight_result(result);

-- Known hardware/driver issues registry
-- Perfect Storm cross-references log patterns against this table
CREATE TABLE infrastructure.known_issue (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host            VARCHAR(100),              -- NULL = applies to all hosts
    component       VARCHAR(100) NOT NULL,     -- 'r8169', 'xrdp', etc.
    pattern         TEXT         NOT NULL,     -- log string to match
    severity        VARCHAR(20)  NOT NULL,     -- 'noise', 'warning', 'critical'
    description     TEXT,                      -- human-readable explanation
    remediation     TEXT,                      -- what to do about it
    added_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

### 5.2 Schema

These tables belong in a new `infrastructure` schema, consistent with
Curator's functional schema naming convention (`identity`, `projects`,
`audit`, `messages`, `infrastructure`).

### 5.3 Messages Integration

When Perfect Storm returns `warn` or `block`, it calls
`api.create_message()` with:

```json
{
  "recipient_id": <captain user id>,
  "sender_label": "perfect_storm",
  "subject": "Preflight check: BLOCK — T490 network instability detected",
  "body": "<full LLM explanation>",
  "source": "infrastructure",
  "notification_level_id": <urgent for block, normal for warn>
}
```

This surfaces in the Curator message center (once built) and triggers
Apprise dispatch per the existing notification design.

---

## 6. Log Processing Pipeline

### 6.1 Collection (Python)

```python
def collect_logs(host: str, window_minutes: int = 60) -> list[str]:
    """
    Fetch log lines from configured sources for a given host.
    Sources come from infrastructure.log_source table via api.*.
    """
    sources = get_log_sources(host)  # api call
    lines = []
    
    for source in sources:
        if source['source_type'] == 'journalctl':
            lines.extend(fetch_journalctl(
                since=f"{window_minutes} minutes ago",
                unit=source.get('unit_filter')
            ))
        elif source['source_type'] == 'file':
            lines.extend(tail_log_file(source['path'], window_minutes))
    
    return lines
```

### 6.2 Preprocessing (Python)

Before handing anything to Qwen, Python builds a structured summary:

```python
def preprocess_logs(lines: list[str]) -> dict:
    return {
        "total_lines": len(lines),
        "window_minutes": window_minutes,
        "error_frequency": count_by_pattern(lines),     # errors per minute
        "top_errors": top_n_patterns(lines, n=10),      # most frequent
        "known_issues_found": cross_reference_known_issues(lines),
        "error_trend": trend_analysis(lines),            # getting worse?
        "cascade_candidates": find_correlated_errors(lines),
        "last_clean_window": last_period_without_errors(lines)
    }
```

### 6.3 LLM Prompt Structure

```python
system_prompt = """
You are a system reliability analyst. You analyze preprocessed log 
summaries to determine whether it is safe to run a new script on a 
system that may be under stress.

You have access to tools:
- query_known_issues: check a component name against the known issues registry
- web_search: look up error messages or driver bugs you don't recognize
- check_resources: get current CPU/memory/network buffer state

Return a JSON object with:
{
  "result": "pass" | "warn" | "block",
  "confidence": 0.0-1.0,
  "summary": "one sentence plain English",
  "reasoning": "explanation of what you found and why",
  "risk_factors": ["list of specific concerns"],
  "recommendation": "what to do before running the script, if anything"
}
"""

user_prompt = f"""
I am about to run this script on host '{host}':
Script: {script_path}
Description: {task_description}

Here is the preprocessed log summary for the last {window_minutes} minutes:
{json.dumps(log_summary, indent=2)}

Known issues already in our registry for this host:
{json.dumps(known_issues, indent=2)}

Is it safe to run this script now?
"""
```

---

## 7. Result Handling

### 7.1 Result States

| Result | Meaning | Curator UI Behavior |
|--------|---------|---------------------|
| `pass` | Logs look clean, safe to proceed | Script runs; result logged |
| `warn` | Issues present but not critical; proceed with awareness | User shown warning + explanation; can override and run |
| `block` | System is at risk; do not run script now | Script does not run; message sent; remediation shown |

### 7.2 Override Handling

A `warn` result presents the explanation and a "Run Anyway" button.
If the user overrides, `script_executed = TRUE` is recorded alongside
the `warn` result — creating an audit trail of "ran despite warning."

A `block` result does not offer an override. It is a hard stop.

---

## 8. Configuration

Consistent with Curator's config-driven design: no hardcoded values.

```yaml
# perfect_storm.yaml
llm:
  host: "localhost"
  port: 8080             # llama-server port
  model: "qwen3-8b"
  temperature: 0.2       # low for consistent analysis
  max_tokens: 2048

log_collection:
  default_window_minutes: 60
  max_lines_before_truncation: 5000
  truncation_strategy: "recent"   # keep most recent lines

thresholds:
  errors_per_minute_warn: 5
  errors_per_minute_block: 20
  known_critical_issue_auto_block: true

hosts:
  t490:
    display_name: "T490 Proxmox Host"
    headscale_address: "100.64.x.x"   # TBD
  wcyj-meet:
    display_name: "Hetzner VPS"
    headscale_address: "100.64.x.x"   # TBD
```

---

## 9. Open Questions

1. **Remote log access:** The T490 is a separate physical machine. How
   does Perfect Storm reach its logs? Options:
   - SSH from MacBook (where LLM runs) to T490
   - A lightweight agent on T490 that exposes logs via HTTP
   - Centralized log forwarding to a syslog server on the network
   TBD — depends on Headscale mesh availability at check time.

2. **Where does Perfect Storm run?** MacBook Air (where Qwen/llama.cpp
   lives) is the natural home for the LLM inference. But the Python
   preprocessing could run on the target host. Architecture TBD.

3. **Script execution mechanism:** How does Curator actually run the
   script? Options:
   - SSH from Curator's host to target
   - A systemd-socket-activated runner on each host
   - A local script runner when Curator runs on the same machine
   This is a significant security surface — needs explicit design before
   implementation.

4. **Task type vs. task tag:** Should "experimental" be a task type
   (new lookup table) or a tag? Type feels cleaner for UI gating logic
   (easier to write "if task.type == 'experimental'" than to scan tags).
   But tags are already in the schema. Decision TBD.

5. **Log window:** Fixed 60 minutes, or configurable per task? A long-
   running known-flaky process might need a longer window.

6. **Known issues registry population:** Who populates it? Manual entry
   via Curator UI? Import from a community database? Currently assumes
   manual entry by the operator.

---

## 10. Implementation Roadmap

**Prerequisites (must exist first):**
- [ ] Fascism Index `tool_agent.py` built and tested
- [ ] `messages` schema built (`api.create_message()` available)
- [ ] `task_type` lookup table added to projects schema
- [ ] `infrastructure` schema created in PostgreSQL

**Phase 1 — Offline validation:**
- [ ] Python log collection and preprocessing (no LLM)
- [ ] Structured summary output to stdout
- [ ] Validate against T490 incident logs: does the summary capture what
      happened?

**Phase 2 — LLM integration:**
- [ ] Connect Qwen via `tool_agent.py`
- [ ] Test preflight prompt with T490 incident logs as input
- [ ] Tune thresholds and prompt based on output quality
- [ ] Add `known_issue` registry and tool

**Phase 3 — Curator integration:**
- [ ] `api.log_preflight_result()` function
- [ ] `api.get_task_type()` function
- [ ] Curator backend: intercept "Run Script" for experimental tasks
- [ ] Curator UI: preflight result display in task detail panel
- [ ] Messages integration: warn/block writes to `messages.messages`

**Phase 4 — Script execution (separate design pass needed):**
- [ ] Security model for remote script execution
- [ ] Execution mechanism (SSH, agent, local)
- [ ] Post-execution log scan (incident analysis)

---

## 11. Relationship to Fascism Index

Both projects share:
- `tool_agent.py` (ToolRegistry, run_agent_turn)
- `web_search` tool implementation
- llama.cpp / llama-server (Qwen via MacBook Air)

Neither project modifies shared infrastructure. Each registers its own
tools against its own ToolRegistry instance. This validates the
registry pattern as genuinely reusable across unrelated problem domains.

---

*Design document prepared July 2026*  
*For: Project Crew homelab infrastructure*  
*Assumes: Fascism Index tool infrastructure complete*  
*Implementation: deferred — design only*
