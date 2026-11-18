# OpportunityLens — Supabase database handoff

This folder contains **review-ready SQL source scripts** for the database
developer. They have **not** been executed against any Supabase project.
The frontend currently works as a guest preview; these tables are the
contract for the planned authenticated MVP.

## Why these files live in database/sql/

As of November 2026, Supabase CLI v3 creates and tracks migrations in
supabase/migrations/<timestamp>_<name>.sql. The developer who applies them
must generate those filenames with the CLI, not invent a timestamp in Git.
These source scripts are organized in dependency order:

1. sql/01_profiles.sql — academic profile linked to Supabase Auth
2. sql/02_opportunities.sql — verified, curated scholarship records
3. sql/03_applications.sql — saved opportunities, applications, tasks
4. sql/04_notifications.sql — consent/preferences and a user inbox

The database is hosted on Supabase PostgreSQL, not in a local SQLite file.
Only the SQL schema and tests belong in the Git repository.

## Developer setup (Supabase CLI v3)

Use a **new, dedicated OpportunityLens** Supabase project. Do not apply these
scripts to another application's database. On the repo branch where the
scripts exist:

1. Check local prerequisites: Docker, Node and Supabase CLI v3. Inspect
   current commands with supabase --version and supabase --help.
2. Run supabase init at repository root if no supabase/config.toml exists.
   Run supabase start to launch the disposable local Supabase stack.
3. Generate the real migration files **in order**, using the CLI's
   documented stdin support:

       supabase migration new profiles < database/sql/01_profiles.sql
       supabase migration new opportunities < database/sql/02_opportunities.sql
       supabase migration new applications < database/sql/03_applications.sql
       supabase migration new notifications < database/sql/04_notifications.sql

4. Run supabase db reset to apply them to the **local** database and inspect
   any SQL error. Then run database/tests/security_assertions.sql against the
   local database using psql or the local SQL editor.
5. Run supabase test db (if you add database-level tests) and
   supabase migration list; run Supabase security and performance advisors.
6. Verify actual access with two different test Auth users and an
   unauthenticated client: a user must never read/write another user's
   profiles, applications, saved items or notifications. An unauthenticated
   client may only read verified published opportunities. A signed-in user
   must not be able to insert or publish an opportunity or forge notifications.
7. Commit the CLI-generated supabase/migrations/*.sql files in your own
   reviewed PR; do not apply or deploy migrations directly from this branch.

**Hosted staging only after review:**

    supabase link --project-ref <STAGING_PROJECT_REF>
    supabase migration list --remote
    supabase db push --remote --yes

The --remote flag is essential with CLI v3: database operations are local by
default. --yes is required for non-interactive hosted mutations; use only
when the target project and changes have been intentionally reviewed.
Have just one developer deploy migrations at a time. Production deployment
requires separate approval and a separate project reference.

Do not create tables by hand in the hosted SQL editor after establishing
migration history. That creates drift between Git and the database.

## Security contract

- public.profiles: only each signed-in owner can SELECT/INSERT/UPDATE/DELETE.
  An auth.users FK uses Supabase Auth IDs; these scripts do not modify
  Supabase-managed auth, storage or realtime schemas.
- public.opportunities: anon/authenticated can SELECT **published and
  verified** records. Only a trusted backend using a secret key may ingest,
  update, archive, or publish them.
- public.saved_opportunities, public.applications, public.application_tasks:
  only the owner can read or write their data. A composite foreign key prevents
  cross-user application tasks.
- public.notification_preferences: owner-only; email and deadline alert
  switches default to FALSE.
- public.notifications: owner can SELECT and update only the read_at column;
  the server alone writes the notification content.
- Every exposed table has explicit GRANT statements, RLS enabled, and
  policies restricted to the intended role. This is necessary after the
  May/October 2026 Data API grant default changes.
- Policies use TO authenticated and (select auth.uid()) ownership checks.
  No user-editable JWT user_metadata is treated as authorization data.
- No SECURITY DEFINER function. The updated_at trigger is SECURITY INVOKER
  with a fixed search path and no public RPC execution privileges.
- Never store raw Gemini/LLM API keys in these tables. If persistent user
  credentials become necessary, design separate encrypted secret storage
  with an explicit threat model first.
- Expose only the Supabase publishable key (sb_publishable_...) in the React
  browser; keep sb_secret_... solely on trusted backend/server infrastructure.
- When Data API exposure is disabled for newly created tables, the explicit
  grants in these scripts are still required, and table exposure settings
  in Dashboard > Integrations > Data API must also be reviewed.

No auth trigger auto-creates profiles: after a successful Auth login, the
client should insert/upsert the signed-in user's profile with user_id set
to the authenticated user ID. Never take that ID from an untrusted backend
request without verifying the JWT.

## Mapping to the current application

The existing Python schemas.py and eligibility_engine.py remain the source
of truth for rule evaluation. The database stores source-derived requirements,
application progress and authenticated profiles; it does NOT replace the
Python eligibility engine. The React preview in web/src/main.jsx currently
keeps state in browser memory; a future integration PR should introduce
Supabase Auth, store/read profiles and checklists through RLS, and keep
backend ingestion separate. Do not claim live discovery or alerts before
the respective services are built.

## Platform references (reviewed November 18, 2026)

- https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically
- https://supabase.com/changelog/supabase-cli-v3
- https://supabase.com/docs/guides/deployment/database-migrations
- https://supabase.com/docs/guides/api/securing-your-api
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/docs/guides/security/production-checklist
