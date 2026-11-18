"""Static guardrails for the Supabase SQL handoff (not DB execution tests).

The developer must still validate the SQL and cross-user RLS behavior
against a disposable local Supabase database (see database/README.md).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "database" / "sql"
SCRIPTS = (
    "01_profiles.sql",
    "02_opportunities.sql",
    "03_applications.sql",
    "04_notifications.sql",
)


def test_each_sql_table_has_explicit_grants_rls_and_policies():
    for filename in SCRIPTS:
        source = (ROOT / filename).read_text(encoding="utf-8").lower()
        # Exclude comments when checking for unsafe executable SQL.
        statements = re.sub(r"--[^\n]*", "", source)
        tables = re.findall(r"\bcreate\s+table\s+public\.([a-z_]+)", statements)
        assert tables, f"Missing table definition in {filename}"
        for table in tables:
            assert (
                f"alter table public.{table} enable row level security"
                in statements
            ), f"RLS is missing for public.{table}"
            assert re.search(
                rf"\bgrant\b[^;]*\bon\s+table\s+public\.{table}\b",
                statements,
            ), f"Explicit Data API grant missing for public.{table}"
            assert re.search(
                rf"\bon\s+public\.{table}\s+for\s+",
                statements,
            ), f"No policy for public.{table}"

        assert "auth.role()" not in statements
        assert "security definer" not in statements


def test_owner_boundaries_and_read_only_catalog():
    profile = (ROOT / SCRIPTS[0]).read_text(encoding="utf-8").lower()
    catalog = (ROOT / SCRIPTS[1]).read_text(encoding="utf-8").lower()
    apps = (ROOT / SCRIPTS[2]).read_text(encoding="utf-8").lower()
    messages = (ROOT / SCRIPTS[3]).read_text(encoding="utf-8").lower()

    assert "references auth.users" in profile
    assert "using (user_id = (select auth.uid()))" in profile
    assert "with check (user_id = (select auth.uid()))" in profile
    assert "grant select on table public.opportunities to anon, authenticated" in catalog
    assert "on public.opportunities for select to anon, authenticated" in catalog
    assert "status = 'published' and last_verified_at is not null" in catalog
    assert "foreign key (application_id, user_id)" in apps
    assert "grant update (read_at) on table public.notifications" in messages
    assert "on public.notifications for insert to authenticated" not in messages
    assert "grant all on table public.notifications to authenticated" not in messages


def test_handoff_requires_local_review_before_remote_changes():
    doc = (ROOT.parent / "README.md").read_text(encoding="utf-8").lower()
    assert "have **not** been executed" in doc
    assert "supabase migration new" in doc
    assert "supabase db reset" in doc
    assert "supabase db push --remote --yes" in doc
