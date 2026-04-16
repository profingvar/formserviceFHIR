-- #60: rename Group.group_type → Group.category, loosen enum → varchar.
--
-- Background: the column was a 4-value Postgres enum (planning, request,
-- provider, analysis) tied to the old pre-#57 model where group_type
-- granted phase access. After #57 groups are orthogonal to phases and
-- the old 4-value taxonomy is no longer meaningful — SU should be able
-- to invent new category labels without a schema migration.
--
-- Tables touched:
--   groups.group_type           → groups.category            (varchar(64))
--   group_proposals.group_type  → group_proposals.category   (varchar(64))
-- Type dropped:
--   group_type_enum
--
-- This script is idempotent: each step checks current state first so it
-- is safe to re-run on an environment that is already partially migrated.
-- Run inside a single transaction so a failure anywhere leaves nothing
-- half-renamed.
--
-- Usage:
--   docker exec sso_db psql -U ssouser -d ssodb \
--     -f /tmp/rename_group_type_to_category.sql
-- (copy the file in with `docker cp` first, or pipe via stdin).

BEGIN;

-- ---------------------------------------------------------------
-- groups.group_type  →  groups.category
-- ---------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'groups' AND column_name = 'group_type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'groups' AND column_name = 'category'
    ) THEN
        -- Drop the enum constraint by changing the type to varchar first,
        -- then rename. Doing it in this order keeps existing row values
        -- intact (enum literals become their string names).
        ALTER TABLE groups
            ALTER COLUMN group_type TYPE varchar(64)
            USING group_type::text;
        ALTER TABLE groups
            RENAME COLUMN group_type TO category;
    END IF;
END$$;

-- ---------------------------------------------------------------
-- group_proposals.group_type  →  group_proposals.category
-- ---------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'group_proposals' AND column_name = 'group_type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'group_proposals' AND column_name = 'category'
    ) THEN
        ALTER TABLE group_proposals
            ALTER COLUMN group_type TYPE varchar(64)
            USING group_type::text;
        ALTER TABLE group_proposals
            RENAME COLUMN group_type TO category;
    END IF;
END$$;

-- ---------------------------------------------------------------
-- Drop the now-orphaned enum type.
-- Guarded so a re-run doesn't error.
-- ---------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'group_type_enum'
    ) THEN
        DROP TYPE group_type_enum;
    END IF;
END$$;

COMMIT;

-- ---------------------------------------------------------------
-- Sanity checks (non-transactional; print for the operator).
-- ---------------------------------------------------------------
SELECT 'groups.category exists' AS check,
       EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'groups' AND column_name = 'category') AS ok;
SELECT 'group_proposals.category exists' AS check,
       EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'group_proposals' AND column_name = 'category') AS ok;
SELECT 'group_type_enum dropped' AS check,
       NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'group_type_enum') AS ok;
