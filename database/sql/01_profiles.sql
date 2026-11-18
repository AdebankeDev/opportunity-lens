-- OpportunityLens schema contract 01/04: student academic profiles.
-- Reviewed for Supabase PostgreSQL and Data API grants (November 2026).
-- This is a SOURCE SCRIPT. The implementer must generate the actual migration
-- with "supabase migration new profiles < database/sql/01_profiles.sql".

create table public.profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null default '' check (char_length(full_name) <= 120),
  country text not null default '' check (char_length(country) <= 80),
  institution text not null default '' check (char_length(institution) <= 160),
  course_of_study text not null default '' check (char_length(course_of_study) <= 160),
  academic_level text not null default '' check (char_length(academic_level) <= 80),
  cgpa numeric(4, 2),
  cgpa_scale numeric(3, 1) not null default 5.0
    check (cgpa_scale in (4.0, 5.0, 7.0)),
  qualifications text not null default ''
    check (char_length(qualifications) <= 3000),
  age smallint check (age between 1 and 120),
  interests text[] not null default '{}'::text[]
    check (cardinality(interests) <= 30),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_cgpa_in_scale check (
    cgpa is null or (cgpa >= 0 and cgpa <= cgpa_scale)
  )
);

-- Invoker-rights trigger function: no SECURITY DEFINER and fixed search_path.
-- No trigger is added to the managed auth.users table.
create function public.touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $function$
begin
  new.updated_at := now();
  return new;
end;
$function$;

revoke all on function public.touch_updated_at() from public, anon, authenticated;

create trigger profiles_touch_updated_at
before update on public.profiles
for each row execute function public.touch_updated_at();

-- The 2026 Data API exposure change requires explicit GRANT in addition to RLS.
revoke all on table public.profiles from anon, authenticated;
grant select, insert, update, delete on table public.profiles to authenticated;
grant all on table public.profiles to service_role;
alter table public.profiles enable row level security;

create policy "profiles_read_own"
on public.profiles for select to authenticated
using (user_id = (select auth.uid()));

create policy "profiles_insert_own"
on public.profiles for insert to authenticated
with check (user_id = (select auth.uid()));

create policy "profiles_update_own"
on public.profiles for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

create policy "profiles_delete_own"
on public.profiles for delete to authenticated
using (user_id = (select auth.uid()));

-- The frontend must create or upsert a row only after Supabase Auth sign-in.
-- auth.users is referenced, never mutated by these scripts.
