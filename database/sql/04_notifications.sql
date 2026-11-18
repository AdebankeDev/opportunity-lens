-- OpportunityLens schema contract 04/04: opt-in alerts and private inbox.
-- No email is sent from SQL: dispatchers and scheduling will be built separately.

create table public.notification_preferences (
  user_id uuid primary key references public.profiles (user_id) on delete cascade,
  email_alerts_enabled boolean not null default false,
  deadline_reminders_enabled boolean not null default false,
  digest_frequency text not null default 'weekly'
    check (digest_frequency in ('daily', 'weekly')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger notification_preferences_touch_updated_at
before update on public.notification_preferences
for each row execute function public.touch_updated_at();

revoke all on table public.notification_preferences from anon, authenticated;
grant select, insert, update, delete on table public.notification_preferences to authenticated;
grant all on table public.notification_preferences to service_role;
alter table public.notification_preferences enable row level security;

create policy "notification_preferences_read_own"
on public.notification_preferences for select to authenticated
using (user_id = (select auth.uid()));

create policy "notification_preferences_insert_own"
on public.notification_preferences for insert to authenticated
with check (user_id = (select auth.uid()));

create policy "notification_preferences_update_own"
on public.notification_preferences for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "notification_preferences_delete_own"
on public.notification_preferences for delete to authenticated
using (user_id = (select auth.uid()));


create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (user_id) on delete cascade,
  opportunity_id uuid references public.opportunities (id) on delete set null,
  kind text not null check (kind in ('new_match', 'deadline', 'update')),
  title text not null check (char_length(btrim(title)) between 1 and 240),
  message text not null default '' check (char_length(message) <= 4000),
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create index notifications_user_unread_idx
on public.notifications (user_id, created_at desc)
where read_at is null;

create index notifications_user_recent_idx
on public.notifications (user_id, created_at desc);

revoke all on table public.notifications from anon, authenticated;
grant select on table public.notifications to authenticated;
-- Column-level privilege prevents clients from changing who owns a notice,
-- forging notification content, or changing creation timestamps.
grant update (read_at) on table public.notifications to authenticated;
grant all on table public.notifications to service_role;
alter table public.notifications enable row level security;

create policy "notifications_read_own"
on public.notifications for select to authenticated
using (user_id = (select auth.uid()));

create policy "notifications_mark_read_own"
on public.notifications for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

-- No authenticated INSERT or DELETE privileges/policies. Only a trusted
-- server-side process may enqueue notifications. Sending mail additionally
-- requires explicit user opt-in and a separate mail delivery service.
