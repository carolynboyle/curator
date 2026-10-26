"""
dbkit.config.postgres.pgpass - Interactive ~/.pgpass setup for PostgreSQL connections.

Prompts for connection details and password, then appends an entry to ~/.pgpass
with correct permissions (0600). Passwords are never written to any other file.

This script is called by the curator setup.py as part of the full setup flow,
but can also be run standalone to add a ~/.pgpass entry for any connection.

Usage:
    python pgpass.py
"""

import getpass
import stat
from pathlib import Path


_PGPASS = Path.home() / ".pgpass"


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


def setup_pgpass() -> None:
    """Prompt for connection details and append an entry to ~/.pgpass."""
    print("\n~/.pgpass setup")
    print("=" * 40)
    print("The password is written only to ~/.pgpass — never to any config file.\n")

    host     = prompt("Host",          "localhost")
    port     = prompt("Port",          "5432")
    database = prompt("Database name", "*")
    user     = prompt("User")
    password = getpass.getpass(f"  Password for {user}: ")

    entry = f"{host}:{port}:{database}:{user}:{password}"

    print(f"\nEntry to be appended to {_PGPASS}:")
    print(f"  {host}:{port}:{database}:{user}:{'*' * len(password)}")

    if _PGPASS.exists():
        print(f"\n  Note: {_PGPASS} already exists — this entry will be appended.")

    print()
    confirm = input("Write this entry? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted. Nothing written.")
        return

    with _PGPASS.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")

    _PGPASS.chmod(stat.S_IRUSR | stat.S_IWUSR)

    print(f"\nEntry appended to {_PGPASS}")
    print("Permissions set to 0600.")


if __name__ == "__main__":
    setup_pgpass()
