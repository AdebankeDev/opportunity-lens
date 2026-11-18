-- OpportunityLens schema contract 03/04: bookmarks, applications and tasks.

create table public.saved_opportunities (
  user_id uuid not null references public.profiles (user_id) on delete cascade,
  opportunity_id uuid not null references public.opportunities (id) on delete cascade,
  notes text not null default '' check (char_length(notes) <= 3000),
  created_at timestamptz not null default now(),
  primary key (user_id, opportunity_id)
);

create index saved_opportunities_recent_idx
on public.saved_opportunities (user_id, created_at desc);

revoke all on table public.saved_opportunities from anon, authenticated;
grant select, insert, update, delete on table public.saved_opportunities to authenticated;
grant all on table public.saved_opportunities to service_role;
alter table public.saved_opportunities enable row level security;

create policy "saved_read_own"
on public.saved_opportunities for select to authenticated
using (user_id = (select auth.uid()));

create policy "saved_insert_own_published"
on public.saved_opportunities for insert to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1 from public.opportunities o
    where o.id = opportunity_id and o.status = 'published'
  )
);

create policy "saved_update_own"
on public.saved_opportunities for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "saved_delete_own"
on public.saved_opportunities for delete to authenticated
using (user_id = (select auth.uid()));


create table public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (user_id) on delete cascade,
  opportunity_id uuid not null references public.opportunities (id) on delete cascade,
  status text not null default 'researching'
    check (status in (
      'researching', 'preparing', 'submitted',
      'awarded', 'rejected', 'withdrawn'
    )),
  notes text not null default '' check (char_length(notes) <= 10000),
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint applications_unique_user_opportunity unique (user_id, opportunity_id),
  -- Composite key lets tasks enforce both the application ID and user owner.
  constraint applications_id_user_unique unique (id, user_id)
);

create trigger applications_touch_updated_at
before update on public.applications
for each row execute function public.touch_updated_at();

create index applications_user_status_idx
on public.applications (user_id, status, updated_at desc);

revoke all on table public.applications from anon, authenticated;
grant select, insert, update, delete on table public.applications to authenticated;
grant all on table public.applications to service_role;
alter table public.applications enable row level security;

create policy "applications_read_own"
on public.applications for select to authenticated
using (user_id = (select auth.uid()));

create policy "applications_insert_own_published"
on public.applications for insert to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1 from public.opportunities o
    where o.id = opportunity_id and o.status = 'published'
  )
);

create policy "applications_update_own"
on public.applications for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "applications_delete_own"
on public.applications for delete to authenticated
using (user_id = (select auth.uid()));


create table public.application_tasks (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null,
  user_id uuid not null,
  category text not null default 'document'
    check (category in ('document', 'action', 'verification')),
  title text not null check (char_length(btrim(title)) between 1 and 240),
  detail text,
  completed boolean not null default false,
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint application_tasks_application_owner_fk
    foreign key (application_id, user_id)
    references public.applications (id, user_id)
    on delete cascade
);

create trigger application_tasks_touch_updated_at
before update on public.application_tasks
for each row execute function public.touch_updated_at();

create index application_tasks_application_order_idx
on public.application_tasks (application_id, position, id);

create index application_tasks_owner_idx
on public.application_tasks (user_id);

revoke all on table public.application_tasks from anon, authenticated;
grant select, insert, update, delete on table public.application_tasks to authenticated;
grant all on table public.application_tasks to service_role;
alter table public.application_tasks enable row level security;

create policy "tasks_read_own"
on public.application_tasks for select to authenticated
using (user_id = (select auth.uid()));

create policy "tasks_insert_own"
on public.application_tasks for insert to authenticated
with check (user_id = (select auth.uid()));

create policy "tasks_update_own"
on public.application_tasks for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "tasks_delete_own"
on public.application_tasks for delete to authenticated
using (user_id = (select auth.uid()));

-- The composite FK prevents writing a task against somebody else's
-- application even when a client manipulates application_id.
