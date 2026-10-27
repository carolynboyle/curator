"""
contactkit.cli - Command-line interface for contactkit.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dbkit.config import ConfigManager
from dbkit.connection import AsyncDBConnection

from contactkit.plugins.imports.gmail import GmailImporter
from contactkit.logger import logger


async def cmd_import(args) -> int:
    """
    Import contacts from file.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Determine importer
    if args.format == "gmail":
        importer = GmailImporter()
    else:
        print(f"Unknown format: {args.format}", file=sys.stderr)
        return 1

    # Check file exists
    if not Path(args.file).exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1

    # Get database connection
    try:
        config = ConfigManager()
        db = AsyncDBConnection(config)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        return 1

    # Run import
    try:
        logger.info(f"Starting {importer.name} import from {args.file}")

        result = await importer.import_contacts(
            args.file,
            db,
            dry_run=args.dry_run,
        )

        # Log results
        logger.info(
            f"Import complete: {result.contacts_created} contacts, "
            f"{result.emails_created} emails, {result.phones_created} phones"
        )

        if result.errors_count > 0:
            logger.warning(f"{result.errors_count} errors encountered:")
            for error in result.error_log:
                logger.warning(f"  {error}")

        if result.errors_count > 0:
            return 1

        return 0

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


async def cmd_list_formats(args) -> int:
    """List available importers."""
    print("Available import formats:")
    print("  gmail   - Google Contacts CSV export")
    print("  proton  - Proton Contacts VCF (not yet implemented)")
    print("  outlook - Outlook CSV (not yet implemented)")
    print("  apple   - Apple Contacts VCF (not yet implemented)")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="contactkit - Contact importer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # import subcommand
    import_parser = subparsers.add_parser("import", help="Import contacts from file")
    import_parser.add_argument(
        "--format",
        choices=["gmail", "proton", "outlook", "apple"],
        default="gmail",
        help="Import format (default: gmail)",
    )
    import_parser.add_argument(
        "--file",
        required=True,
        help="Path to import file",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse but don't commit to database",
    )
    import_parser.set_defaults(func=cmd_import)

    # list-formats subcommand
    list_parser = subparsers.add_parser(
        "list-formats",
        help="List available import formats",
    )
    list_parser.set_defaults(func=cmd_list_formats)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        exit_code = asyncio.run(args.func(args))
        return exit_code
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
