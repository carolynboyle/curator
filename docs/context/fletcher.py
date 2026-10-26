"""
fletcher.py - GitHub URL manifest generator

Part of the dev-utils toolkit / Project Crew.
Reads a Dr. Filewalker manifest YAML and generates a .fletch manifest
with GitHub URLs for all project files.

Suitable for use by agents (raw URLs) or humans (web URLs).

Usage:
    fletcher                          (interactive — detects manifest in .doc-gen/)
    fletcher --repo https://...       (explicit repo, still warns on mismatch)
    fletcher --branch main
    fletcher --web
    fletcher --output urls.fletch

Config (~/.config/dev-utils/config.yaml):
    fletcher:
      repos:
        - https://github.com/carolynboyle/projs
        - https://github.com/carolynboyle/doc-gen
      branch: master
      url_type: raw

Logs:
    ~/.local/share/dev-utils/fletcher.log       (human-readable)
    ~/.local/share/dev-utils/fletcher.json.log  (JSON, one object per line)
"""

import argparse
import json
import logging
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path

import yaml


CONFIG_PATH    = Path.home() / ".config" / "dev-utils" / "config.yaml"
DOC_GEN_MANIFEST = Path(".doc-gen") / "manifest.yml"
LOG_DIR        = Path.home() / ".local" / "share" / "dev-utils"
LOG_PATH       = LOG_DIR / "fletcher.log"
JSON_LOG_PATH  = LOG_DIR / "fletcher.json.log"

RAW_BASE = "https://raw.githubusercontent.com"
WEB_BASE = "https://github.com"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "level":   record.levelname,
                "tool":    "fletcher",
                "message": record.getMessage(),
            }
        )


def _setup_logging() -> None:
    """
    Configure the root logger with two file handlers:
      - fletcher.log       plain text, INFO+
      - fletcher.json.log  JSON lines, INFO+

    Also adds a stderr handler at WARNING+ so important messages
    surface in the terminal without drowning normal output.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("fletcher")
    logger.setLevel(logging.DEBUG)  # handlers filter individually

    plain_fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # -- plain text log file --------------------------------------------------
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(plain_fmt)
    logger.addHandler(fh)

    # -- JSON log file --------------------------------------------------------
    jh = logging.FileHandler(JSON_LOG_PATH, encoding="utf-8")
    jh.setLevel(logging.INFO)
    jh.setFormatter(_JsonFormatter())
    logger.addHandler(jh)

    # -- stderr (warnings and above only) -------------------------------------
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)


log = logging.getLogger("fletcher")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load full dev-utils config. Returns empty dict if missing."""
    if CONFIG_PATH.exists():
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text())
            log.debug("Loaded config from %s", CONFIG_PATH)
            return data or {}
        except (yaml.YAMLError, OSError) as e:
            log.warning("Could not load config %s: %s", CONFIG_PATH, e)
    return {}


def save_repo_to_config(repo: str) -> None:
    """Add repo URL to saved list in config if not already present."""
    config = load_config()
    fletcher_cfg = config.setdefault("fletcher", {})
    repos = fletcher_cfg.setdefault("repos", [])

    if repo not in repos:
        repos.append(repo)
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False))
            log.info("Saved repo to config: %s", repo)
        except OSError as e:
            log.warning("Could not save config: %s", e)


# ---------------------------------------------------------------------------
# Git detection
# ---------------------------------------------------------------------------

def detect_git_repo() -> str | None:
    """
    Attempt to detect the GitHub repo URL from git remote origin.
    Returns the URL string, or None if detection fails for any reason.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # Normalise SSH to HTTPS
        if url.startswith("git@github.com:"):
            url = "https://github.com/" + url[len("git@github.com:"):].removesuffix(".git")
        elif url.endswith(".git"):
            url = url.removesuffix(".git")
        if url:
            log.debug("Detected git remote: %s", url)
            return url
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        log.debug("Could not detect git remote origin")
        return None


# ---------------------------------------------------------------------------
# doc-gen check
# ---------------------------------------------------------------------------

def ensure_doc_gen_manifest() -> Path:
    """
    Check that .doc-gen/manifest.yml exists in the current directory.

    If missing, offer to run doc-gen interactively. Exits if the manifest
    still can't be found after doc-gen returns.
    """
    if DOC_GEN_MANIFEST.exists():
        log.debug("Found doc-gen manifest: %s", DOC_GEN_MANIFEST)
        return DOC_GEN_MANIFEST

    log.warning("No %s found in current directory", DOC_GEN_MANIFEST)
    print(f"No {DOC_GEN_MANIFEST} found in current directory.")
    answer = input("Run doc-gen now to create it? [Y/n]: ").strip().lower()

    if answer in ("", "y", "yes"):
        try:
            subprocess.run(["doc-gen"], check=False)
        except FileNotFoundError:
            log.error("doc-gen is not installed or not in PATH")
            print("Error: doc-gen is not installed or not in PATH.", file=sys.stderr)
            sys.exit(1)

        if DOC_GEN_MANIFEST.exists():
            log.info("doc-gen manifest created: %s", DOC_GEN_MANIFEST)
            return DOC_GEN_MANIFEST

    log.error("Cannot continue without %s", DOC_GEN_MANIFEST)
    print(
        f"Cannot continue without {DOC_GEN_MANIFEST}. "
        "Run doc-gen in this directory first, then re-run fletcher.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Repo selection
# ---------------------------------------------------------------------------

def select_repo(config: dict, cli_repo: str | None) -> str:
    """
    Determine the repo URL to use.

    Priority:
      1. --repo flag (bypass menu, but still warn on git mismatch)
      2. Interactive selection from saved repos or new entry

    Always attempts git detection for mismatch warnings.
    """
    detected = detect_git_repo()

    if cli_repo:
        if detected and detected != cli_repo:
            log.warning(
                "--repo %r does not match detected origin %r — using --repo value",
                cli_repo,
                detected,
            )
            print(
                f"Warning: --repo {cli_repo!r} does not match "
                f"detected origin {detected!r}. Continuing with --repo value."
            )
        log.info("Using repo from --repo flag: %s", cli_repo)
        return cli_repo

    repos = config.get("fletcher", {}).get("repos", [])

    # Build the menu
    if repos:
        print("\nSaved repos:")
        for i, r in enumerate(repos, 1):
            print(f"  {i}. {r}")
        print("  A. Use a different repo")
        print()

        while True:
            raw = input("Selection: ").strip()
            if raw.lower() == "a":
                break
            try:
                idx = int(raw) - 1
                if 0 <= idx < len(repos):
                    log.info("Using saved repo: %s", repos[idx])
                    return repos[idx]
                print(f"Please enter 1-{len(repos)} or A.")
            except ValueError:
                print(f"Please enter a number or A.")

    # New repo — try git detect first
    if detected:
        answer = input(
            f"Detected {detected!r} for current directory. "
            "Use this? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            save_repo_to_config(detected)
            log.info("Using detected repo: %s", detected)
            return detected

    # Prompt for URL
    while True:
        url = input("Enter GitHub repo URL: ").strip()
        if url:
            save_repo_to_config(url)
            log.info("Using manually entered repo: %s", url)
            return url
        print("Repo URL cannot be empty.")


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_manifest(manifest_path: Path) -> list:
    """
    Load a Dr. Filewalker manifest YAML.
    Returns list of path strings.
    """
    try:
        data = yaml.safe_load(manifest_path.read_text())
        if not data or "documents" not in data:
            log.error("No 'documents' key found in %s", manifest_path)
            print(f"Error: no 'documents' key found in {manifest_path}", file=sys.stderr)
            sys.exit(1)
        paths = [doc["path"] for doc in data["documents"] if "path" in doc]
        log.info("Loaded %d paths from %s", len(paths), manifest_path)
        return paths
    except (yaml.YAMLError, OSError) as e:
        log.error("Could not load manifest %s: %s", manifest_path, e)
        print(f"Error: could not load manifest {manifest_path}: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def read_version_from_pyproject() -> str | None:
    """
    Read version from pyproject.toml in the current directory.

    Returns the version string, or None if pyproject.toml is absent,
    unreadable, or contains no version field.
    Logs a warning if the file exists but no version can be found.
    """
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        log.warning(
            "No pyproject.toml found in current directory — "
            "manifest.fletch will be generated without a version field"
        )
        return None

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        log.warning("Could not read pyproject.toml: %s — manifest will have no version", e)
        return None

    version = data.get("project", {}).get("version")
    if not version:
        log.warning(
            "pyproject.toml found but no [project].version field — "
            "manifest.fletch will be generated without a version field"
        )
        return None

    log.info("Read version %s from pyproject.toml", version)
    return version


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------

def build_raw_url(repo: str, branch: str, path: str) -> str:
    """Build a raw.githubusercontent.com URL for direct file content access."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{RAW_BASE}/{repo_path}/{branch}/{path}"


def build_web_url(repo: str, branch: str, path: str) -> str:
    """Build a github.com/blob URL for human-readable file viewing."""
    repo_path = repo.rstrip("/").removeprefix("https://github.com/")
    return f"{WEB_BASE}/{repo_path}/blob/{branch}/{path}"


# ---------------------------------------------------------------------------
# Manifest building and writing
# ---------------------------------------------------------------------------

def build_url_manifest(paths: list, repo: str, branch: str, url_type: str) -> dict:
    """
    Build the .fletch manifest structure.

    Returns a dict ready for YAML serialization.
    Includes version from pyproject.toml if available.
    Suitable for direct use by consuming scripts via import.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    build_url = build_raw_url if url_type == "raw" else build_web_url

    manifest = {
        "repo":      repo,
        "branch":    branch,
        "url_type":  url_type,
        "generated": now,
    }

    version = read_version_from_pyproject()
    if version:
        manifest["version"] = version

    manifest["files"] = [
        {"path": p, "url": build_url(repo, branch, p)}
        for p in paths
    ]

    return manifest


def write_manifest(manifest: dict, output_path: Path) -> None:
    """
    Write the .fletch manifest to disk.

    Output is valid YAML with a human-readable comment header.
    Any YAML parser can read it — the .fletch extension is identity, not format.
    """
    version_str = f"v{manifest['version']}" if "version" in manifest else "no version"
    header = (
        f"# Generated: {manifest['generated']}\n"
        f"# Repo: {manifest['repo']}\n"
        f"# Branch: {manifest['branch']}\n"
        f"# URL type: {manifest['url_type']}\n"
        f"# Version: {version_str}\n"
        f"# Files: {len(manifest['files'])}\n\n"
    )
    try:
        output_path.write_text(
            header + yaml.dump(manifest, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        log.info(
            "Written: %s (%d files, %s)",
            output_path,
            len(manifest["files"]),
            version_str,
        )
        print(f"Written: {output_path} ({len(manifest['files'])} files, {version_str})")
    except OSError as e:
        log.error("Could not write %s: %s", output_path, e)
        print(f"Error: could not write {output_path}: {e}", file=sys.stderr)
        sys.exit(1)


def default_output_path(manifest_path: Path) -> Path:
    """Generate default output path alongside the input manifest."""
    return manifest_path.parent / f"{manifest_path.stem}.fletch"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _setup_logging()
    log.info("fletcher started")

    parser = argparse.ArgumentParser(
        description="Generate a GitHub URL manifest (.fletch) from a Dr. Filewalker manifest.",
        epilog="Config: ~/.config/dev-utils/config.yaml",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repo URL — bypasses saved repo menu, warns if it mismatches git origin",
    )
    parser.add_argument(
        "--branch",
        help="Branch name (default: from config or 'master')",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Generate web URLs for humans instead of raw URLs for agents",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: .doc-gen/<manifest>.fletch)",
    )

    args = parser.parse_args()

    # Step 1 — ensure doc-gen manifest exists
    manifest_path = ensure_doc_gen_manifest()

    # Step 2 — load config
    config = load_config()
    fletcher_cfg = config.get("fletcher", {})

    # Step 3 — resolve repo
    repo = select_repo(config, args.repo)

    # Step 4 — resolve branch and url_type
    branch = args.branch or fletcher_cfg.get("branch", "master")
    url_type = "web" if args.web else fletcher_cfg.get("url_type", "raw")
    log.info("Branch: %s, URL type: %s", branch, url_type)

    # Step 5 — resolve output path
    output_path = args.output or default_output_path(manifest_path)

    # Step 6 — build and write
    paths = load_manifest(manifest_path)
    manifest = build_url_manifest(paths, repo, branch, url_type)
    write_manifest(manifest, output_path)

    log.info("fletcher finished")


if __name__ == "__main__":
    main()
