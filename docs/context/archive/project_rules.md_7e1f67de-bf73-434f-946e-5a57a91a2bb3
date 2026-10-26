# Project Rules

## Philosophy

Good code is code that does one thing well, can be understood six months later, and doesn't make the next developer (including future-you) clean up after it. Complexity is not sophistication. A small, clean module that composes well is worth more than a large, clever one that doesn't.

These rules exist so that decisions don't have to be re-made every time. When in doubt, come back here.

---

## Python Standards

- **Object Oriented.** Model the problem domain as classes with clear responsibilities. Avoid loose collections of functions where an object makes more sense.
- **Small modules over monoliths.** Each module does one thing. If you have to reach for "and" to describe what a module does, it should probably be two modules.
- **DRY — Don't Repeat Yourself.** If the same logic appears in two places, it belongs in one place. The second time you write something similar, refactor.
- **No hard-coded variables.** Application configuration — labels, menus, platform paths, defaults, lists of options — lives in external config files (`yaml` or `json` as appropriate). Code loads config; code does not contain config. Algorithmic constants intrinsic to the code itself (`MAX_RETRIES`, `DEFAULT_TIMEOUT`) may live in code.
- **Config hierarchy:** shipped `data/` files are the default. User config in `~/.appname/` overrides them. Never the reverse.
- **Single source of truth.** Any given operation has exactly one canonical implementation. CLI and GUI both call it. Neither owns it.
- **Identify reusable code early.** If a class or utility could reasonably be used in another project, flag it as a personal library candidate. Don't wait until it's tangled up to notice.
- **Write code that doesn't make assumptions about OS file io** always specify encoding='utf-8' explicitly in read_text(), open(), and any other file I/O calls. This will save much pain when porting to Windows/Mac?Chrome.


---

## Architecture Rules

### Module Structure
- One class or one cohesive set of related functions per module.
- `data/` directory ships with the package and contains all defaults.
- User-facing config lives outside the package, in a well-known location (`~/.appname/`).

### CLI / GUI Parity
- **CLI first.** No feature exists in the GUI that does not exist in the CLI — unless it's something only a GUI can do.
- **GUI is a visualizer.** The GUI's job is to surface CLI functionality in a way that shows a lot of information at a glance. It does not own logic.
- **Feature parity is a hard rule.** If you add something to one interface, add it to the other before the work is considered done.

### Config and Data
- YAML for human-readable config (menus, defaults, platform definitions, preferences).
- JSON where interoperability with other tools or APIs is needed.
- Never parse config inline. Load it through a dedicated config module.

---

## Testing Requirements

- **Unit tests are required, not optional.** New functionality is not done until it has tests.
- Test the logic, not the framework. Mock external dependencies (filesystem, tmux, network) so tests are fast and reliable.
- **Integration tests** cover the full round-trip for critical paths: project creation, manifest read/write, session management, config load/override.
- Tests live in `tests/` and mirror the structure of `src/`.
- A passing Pylint run is part of done. No merging code with linting errors.

---

## Personal Library Candidates

Promote code to a personal library when:
- It has been used (or would clearly be useful) in more than one project.
- It has no hard dependency on the parent project's internals.
- It can be given a clear, general name without forcing it.

Current candidates identified in this project:
- `MenuBuilder` — YAML-driven menu construction
- `PromptHelper` — CLI input/confirmation utilities
- `TodoManager` — `todo.md` lifecycle management

> **Coming soon:** A shared repo for personal library items. If it's useful to you, it's probably something the rest of us need. More on this shortly.

---

## Secrets Handling

> **Coming soon:** Full section on secrets management, SSH credentials, and keychain integration. Placeholder rules until then:
> - Secrets never in code or config files.
> - Secrets never in the manifest — manifests hold *references*, not values.
> - Use the system keychain (`keyring` in Python) as the default store.
> - No hidden background processes. Everything the app does with credentials is explicit and visible.

---

## Contributor Guidelines

Welcome. Please read this section before opening a PR.

### What we care about
- **Clean, readable code over clever code.** If it needs a comment to explain what it does, it probably needs to be rewritten.
- **One thing per module, one module per thing.**
- **No hard-coded values.** If you're adding a default, a label, or a list of options, it goes in a `data/` YAML file, not in the Python.
- **Tests come with the code.** PRs without tests for new functionality will not be merged.
- **CLI parity.** If you add a GUI feature and it's something that could be done in the CLI, have pity on those of us who sometimes live in SSH land and make sure the CLI can do it too. Unless it's obviously something only a GUI can do.

### Before you submit
- Pylint passes with no errors.
- New tests written and passing.
- Config/data changes are in the appropriate `data/` files, not hardcoded.
- If your change touches the manifest schema or config structure, document it.

### Style
- Follow existing patterns in the codebase before reaching for something new.
- If you think a pattern in the codebase is wrong, you could very well be right about that. Help us all out by opening an issue before rewriting it.
