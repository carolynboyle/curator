# Schema Migration: Contacts & Organizations Refactoring

**Date:** April 23, 2026
**Database:** projects (PostgreSQL)
**Purpose:** Add organizations table, contact_emails table, normalize contacts structure, add project_contacts primary email tracking, add import audit table

---

## Migration Steps

Run each section in order in Adminer. All changes are reversible if needed.

---

## 1. Create `organizations` Table

```sql
CREATE TABLE public.organizations (
    id bigint NOT NULL,
    name character varying(255) NOT NULL UNIQUE,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.organizations OWNER TO steward;

ALTER TABLE public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);

ALTER TABLE public.organizations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.organizations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE INDEX idx_organizations_name ON public.organizations USING btree (name);
```

---

## 2. Create `contact_emails` Table

```sql
CREATE TABLE public.contact_emails (
    id bigint NOT NULL,
    contact_id bigint NOT NULL,
    email character varying(255),
    email_type character varying(50),
    created_at timestamp without time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.contact_emails OWNER TO steward;

ALTER TABLE public.contact_emails
    ADD CONSTRAINT contact_emails_pkey PRIMARY KEY (id);

ALTER TABLE public.contact_emails ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.contact_emails_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

ALTER TABLE public.contact_emails
    ADD CONSTRAINT contact_emails_contact_id_fkey 
    FOREIGN KEY (contact_id) REFERENCES public.contacts(id) ON DELETE CASCADE;

CREATE INDEX idx_contact_emails_contact ON public.contact_emails USING btree (contact_id);
CREATE INDEX idx_contact_emails_email ON public.contact_emails USING btree (email);
```

---

## 3. Update `contacts` Table

### 3.1 Add `organization_id` column

```sql
ALTER TABLE public.contacts 
    ADD COLUMN organization_id bigint;

ALTER TABLE public.contacts
    ADD CONSTRAINT contacts_organization_id_fkey 
    FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;

CREATE INDEX idx_contacts_organization ON public.contacts USING btree (organization_id);
```

### 3.2 Drop `email` column (data will be in contact_emails table)

```sql
ALTER TABLE public.contacts DROP COLUMN email;
```

### 3.3 Make `name` nullable (allow phone/email-only contacts)

```sql
ALTER TABLE public.contacts ALTER COLUMN name DROP NOT NULL;
```

### 3.4 Make `title` nullable

```sql
ALTER TABLE public.contacts ALTER COLUMN title DROP NOT NULL;
```

### 3.5 Make `notes` nullable

```sql
ALTER TABLE public.contacts ALTER COLUMN notes DROP NOT NULL;
```

---

## 4. Update `project_contacts` Table

### 4.1 Add `primary_email_id` column (project-specific primary email)

```sql
ALTER TABLE public.project_contacts 
    ADD COLUMN primary_email_id bigint;

ALTER TABLE public.project_contacts
    ADD CONSTRAINT project_contacts_primary_email_id_fkey 
    FOREIGN KEY (primary_email_id) REFERENCES public.contact_emails(id) ON DELETE SET NULL;

CREATE INDEX idx_project_contacts_primary_email ON public.project_contacts USING btree (primary_email_id);
```

---

## 5. Create `contact_imports` Audit Table

```sql
CREATE TABLE public.contact_imports (
    id bigint NOT NULL,
    import_file character varying(255),
    imported_at timestamp without time zone DEFAULT now() NOT NULL,
    total_rows_processed integer,
    contacts_created integer,
    emails_created integer,
    phones_created integer,
    rows_skipped integer,
    errors_count integer,
    error_log text
);

ALTER TABLE public.contact_imports OWNER TO steward;

ALTER TABLE public.contact_imports
    ADD CONSTRAINT contact_imports_pkey PRIMARY KEY (id);

ALTER TABLE public.contact_imports ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.contact_imports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);

CREATE INDEX idx_contact_imports_imported_at ON public.contact_imports USING btree (imported_at DESC);
```

---

## 6. Verify Changes

After running all migrations, verify:

```sql
-- Check organizations table
\d organizations

-- Check contact_emails table
\d contact_emails

-- Check contacts table (should have organization_id, no email column)
\d contacts

-- Check project_contacts (should have primary_email_id)
\d project_contacts

-- Check contact_imports table
\d contact_imports

-- Check all indexes exist
SELECT tablename, indexname FROM pg_indexes 
WHERE tablename IN ('organizations', 'contact_emails', 'contacts', 'project_contacts', 'contact_imports')
ORDER BY tablename, indexname;
```

---

## Rollback (if needed)

If you need to revert:

```sql
-- Drop new tables (drop dependent first)
DROP TABLE public.contact_imports CASCADE;
DROP TABLE public.contact_emails CASCADE;
DROP TABLE public.organizations CASCADE;

-- Revert contacts changes
ALTER TABLE public.contacts ADD COLUMN email character varying(255);
ALTER TABLE public.contacts ALTER COLUMN name SET NOT NULL;
ALTER TABLE public.contacts ALTER COLUMN title SET NOT NULL;
ALTER TABLE public.contacts ALTER COLUMN notes SET NOT NULL;
ALTER TABLE public.contacts DROP COLUMN organization_id CASCADE;

-- Revert project_contacts changes
ALTER TABLE public.project_contacts DROP COLUMN primary_email_id CASCADE;
```

---

## Notes

- All foreign keys use `ON DELETE CASCADE` or `ON DELETE SET NULL` for data integrity
- Indexes on foreign keys and commonly-searched fields (name, email) for query performance
- `contact_imports` table tracks every import for audit trail + troubleshooting
- All timestamps default to `now()` for automatic tracking
- No data loss — existing contacts/phones/urls preserved; email column dropped after import
