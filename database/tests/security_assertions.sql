-- Manual/local-only security assertions.
-- Run AFTER all four generated migrations on a disposable local Supabase DB.
-- This checks structural safeguards, NOT actual cross-user request behavior.
do $verify$
declare
  table_name text;
  expected_tables text[] := array[
    'profiles', 'opportunities', 'saved_opportunities',
    'applications', 'application_tasks', 'notification_preferences',
    'notifications'
  ];
begin
  foreach table_name in array expected_tables loop
    if not exists (
      select 1
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public'
        and c.relname = table_name
        and c.relkind in ('r', 'p')
        and c.relrowsecurity
    ) then
      raise exception 'RLS missing or table absent: public.%', table_name;
    end if;

    if not exists (
      select 1 from pg_policies p
      where p.schemaname = 'public'
        and p.tablename = table_name
    ) then
      raise exception 'No RLS policies exist for public.%', table_name;
    end if;
  end loop;

  if has_table_privilege('anon', 'public.profiles', 'SELECT')
     or has_table_privilege('anon', 'public.applications', 'SELECT')
     or has_table_privilege('anon', 'public.notifications', 'SELECT') then
    raise exception 'Private user data is directly selectable by anon';
  end if;

  if not has_table_privilege('anon', 'public.opportunities', 'SELECT') then
    raise exception 'Publicly published opportunities are not exposed';
  end if;

  if has_table_privilege('authenticated', 'public.opportunities', 'INSERT')
     or has_table_privilege('authenticated', 'public.opportunities', 'UPDATE') then
    raise exception 'Authenticated users must not modify the opportunity catalog';
  end if;

  if has_table_privilege('authenticated', 'public.notifications', 'INSERT')
     or has_table_privilege('authenticated', 'public.notifications', 'DELETE') then
    raise exception 'Authenticated users must not forge/delete notifications';
  end if;

  if has_column_privilege('authenticated', 'public.notifications', 'title', 'UPDATE')
     or not has_column_privilege('authenticated', 'public.notifications', 'read_at', 'UPDATE') then
    raise exception 'Notification update privileges must cover read_at only';
  end if;

  raise notice 'Structural RLS/grants checks passed; now test cross-user access';
end;
$verify$;
