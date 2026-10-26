"""
dbkit postgres setup - Interactive configuration setup for dbkit PostgreSQL connections.

Prompts for connection details and writes ~/.config/dev-utils/config.yaml,
then calls the pgpass setup to add the password entry to ~/.pgpass.

Usage:
    python setup.py
"""

from pathlib import Path
import sys
import yaml

from pgpass import setup_pgpass


_TEMPLATE = Path(__file__).parent / "config.yaml.template"
_OUTPUT = Path.home() / ".config" / "dev-utils" / "config.yaml"


def prompt(label: str, default: str = "") -> str:
    """Prompt for a value, showing default if provided."""
    if default:
        value = input(f"  {label} [{default}]: ").strip()
        return value if value else default
    else:
        while True:
            value = input(f"  {label}: ").strip()
            if value:
                return value
            print(f"  {label} is required.")


def main() -> None:
    print("\ndbkit PostgreSQL configuration setup")
    print("=" * 40)
    print("Connection details go into ~/.config/dev-utils/config.yaml.")
    print("The password will be set up separately in ~/.pgpass.\n")

    host   = prompt("Host", "localhost")
    port   = prompt("Port", "5432")
    dbname = prompt("Database name")
    user   = prompt("User")

    print("\nConfiguration to be written to:")
    print(f"  {_OUTPUT}\n")
    print("  dbkit:")
    print(f"    host:   {host}")
    print(f"    port:   {port}")
    print(f"    dbname: {dbname}")
    print(f"    user:   {user}")

    print()
    confirm = input("Write this configuration? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted. Nothing written.")
        sys.exit(0)

    config = {
        "dbkit": {
            "host":   host,
            "port":   int(port),
            "dbname": dbname,
            "user":   user,
        }
    }

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"\nWritten to {_OUTPUT}")
    print("\nNow setting up ~/.pgpass for the database password...")
    setup_pgpass()


if __name__ == "__main__":
    main()
