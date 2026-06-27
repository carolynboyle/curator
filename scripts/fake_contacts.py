"""Seed script — generate fake contacts and organizations for development.

Usage:
    python scripts/fake_contacts.py

Reads database connection from ~/.config/dev-utils/config.yaml (same as app).
Inserts into identity.contacts, identity.organizations,
and identity.organization_contacts.

Safe to run multiple times — checks for existing data before inserting.
"""

import asyncio
import random
import sys
from pathlib import Path

from faker import Faker

# Add project root to path so curator imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbkit.connection import AsyncDBConnection

fake = Faker()

NUM_ORGS     = 15
NUM_CONTACTS = 40


async def seed(db: AsyncDBConnection) -> None:
    """Insert fake orgs and contacts if tables are empty."""

    # -- Check existing data --------------------------------------------------
    existing_orgs = await db.fetch_one("SELECT COUNT(*) AS n FROM identity.organizations")
    existing_contacts = await db.fetch_one("SELECT COUNT(*) AS n FROM identity.contacts")

    if existing_orgs["n"] > 0 or existing_contacts["n"] > 0:
        print(f"Data already exists: {existing_orgs['n']} orgs, "
              f"{existing_contacts['n']} contacts. Skipping seed.")
        print("Delete existing rows first if you want to re-seed.")
        return

    # -- Insert organizations -------------------------------------------------
    org_ids = []
    for _ in range(NUM_ORGS):
        result = await db.fetch_one(
            """
            INSERT INTO identity.organizations (name, notes)
            VALUES (%s, %s)
            RETURNING id
            """,
            (fake.company(), fake.catch_phrase())
        )
        org_ids.append(result["id"])
        print(f"  org {result['id']} inserted")

    # -- Insert contacts ------------------------------------------------------
    contact_ids = []
    for _ in range(NUM_CONTACTS):
        result = await db.fetch_one(
            """
            INSERT INTO identity.contacts (name, title, notes)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fake.name(), fake.job(), fake.sentence())
        )
        cid = result["id"]
        contact_ids.append(cid)
        print(f"  contact {cid} inserted")

        # Add a primary email
        await db.execute(
            """
            INSERT INTO identity.contact_emails (contact_id, label, address)
            VALUES (%s, %s, %s)
            """,
            (cid, "work", fake.email())
        )

        # Add a phone (70% of contacts)
        if random.random() < 0.7:
            await db.execute(
                """
                INSERT INTO identity.contact_phones (contact_id, label, number)
                VALUES (%s, %s, %s)
                """,
                (cid, "work", fake.phone_number())
            )

    # -- Link contacts to orgs (most contacts belong to one org) --------------
    used_pairs = set()
    for cid in contact_ids:
        # 80% of contacts belong to at least one org
        if random.random() < 0.8:
            org_id = random.choice(org_ids)
            pair = (org_id, cid)
            if pair not in used_pairs:
                used_pairs.add(pair)
                await db.execute(
                    """
                    INSERT INTO identity.organization_contacts (organization_id, contact_id)
                    VALUES (%s, %s)
                    """,
                    (org_id, cid)
                )

        # 20% of contacts belong to a second org
        if random.random() < 0.2:
            org_id = random.choice(org_ids)
            pair = (org_id, cid)
            if pair not in used_pairs:
                used_pairs.add(pair)
                await db.execute(
                    """
                    INSERT INTO identity.organization_contacts (organization_id, contact_id)
                    VALUES (%s, %s)
                    """,
                    (org_id, cid)
                )

    print(f"\nDone. {NUM_ORGS} organizations, {NUM_CONTACTS} contacts seeded.")


async def main() -> None:
    """Load config and run seed."""
    async with AsyncDBConnection() as db:
        await seed(db)



if __name__ == "__main__":
    asyncio.run(main())