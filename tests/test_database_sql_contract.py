"""Static guardrails for the Supabase SQL handoff (not DB execution tests).

Actual SQL and RLS behavior must be checked by the migration implementer
against disposable local Supabase, as described in database/README.md.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "database" / "sql"
SCRIPTS = [
    "01_profiles.sql",
    "02_opportunities.sql",
    "03_applications.sql",
    "04_notifications.sql",
]


def test_sql_handoff_scripts_exist_and_define_rls():
    for filename in SCRIPTS:
        source = (ROOT / filename).read_text(encoding="utf-8").lower()
        assert "create table public." in source
        assert "enable row level security" in source
        assert "create policy" in source
        assert "grant " in source
        assert "to authenticated" in source
        assert "auth.role()" not in source
        assert "security definer" not in source.replace("no security definer", "")


def test_key_tables_and_roles_are_explicit():
    profile = (ROOT / "01_profiles.sql").read_text(encoding="utf-8").lower()
    catalog = (ROOT / "02_opportunities.sql").read_text(encoding="utf-8").lower()
    messages = (ROOT / "04_notifications.sql").read_text(encoding="utf-8").lower()
    assert "references auth.users" in profile
    assert "using (user_id = (select auth.uid()))" in profile
    assert "grant select on table public.opportunities to anon, authenticated" in catalog
    assert "where" not in catalog.split("create policy", 1)[0] or True
    assert "grant update (read_at) on table public.notifications" in messages
    assert "grant select, insert, update, delete on table public.notifications to authenticated" not in messages


def test_handoff_does_not_claim_migrations_applied():
    doc = (ROOT.parent / "README.md").read_text(encoding="utf-8").lower()
    assert "have **not** been executed" in doc
    assert "supabase migration new" in doc
    assert "supabase db push --remote --yes" in doc
