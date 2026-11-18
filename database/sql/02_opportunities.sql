-- OpportunityLens schema contract 02/04: curated official opportunities.
-- Public users may read only published, verified records; ingestion writes use
-- a trusted server-side Supabase secret key, never a browser publishable key.

create table public.opportunities (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(btrim(title)) between 3 and 240),
  organizing_institution text not null default ''
    check (char_length(organizing_institution) <= 240),
  category text not null default 'scholarship'
    check (category in (
      'scholarship', 'internship', 'fellowship', 'grant', 'training', 'other'
    )),
  description text not null default '',
  status text not null default 'draft'
    check (status in ('draft', 'published', 'archived')),
  source_url text not null
    check (source_url ~* '^https://[^[:space:]]+$'),
  official_url text
    check (official_url is null or official_url ~* '^https://[^[:space:]]+$'),
  eligible_countries text[] not null default '{}'::text[],
  open_to_all_countries boolean not null default false,
  academic_level_requirements text[] not null default '{}'::text[],
  course_restrictions text[] not null default '{}'::text[],
  cgpa_minimum numeric(4, 2) check (cgpa_minimum >= 0),
  cgpa_scale numeric(3, 1)
    check (cgpa_scale is null or cgpa_scale > 0),
  minimum_age smallint check (minimum_age between 1 and 120),
  maximum_age smallint check (maximum_age between 1 and 120),
  other_eligibility_conditions text[] not null default '{}'::text[],
  required_documents jsonb not null default '[]'::jsonb
    check (jsonb_typeof(required_documents) = 'array'),
  benefits text[] not null default '{}'::text[],
  application_instructions text,
  deadline_raw text,
  deadline_date date,
  evidence jsonb not null default '{}'::jsonb
    check (jsonb_typeof(evidence) = 'object'),
  extraction_notes text,
  last_verified_at timestamptz,
  source_published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint opportunities_cgpa_bounds check (
    cgpa_minimum is null
    or cgpa_scale is null
    or cgpa_minimum <= cgpa_scale
  ),
  constraint opportunities_age_bounds check (
    minimum_age is null
    or maximum_age is null
    or minimum_age <= maximum_age
  ),
  constraint opportunities_published_must_be_verified check (
    status <> 'published' or last_verified_at is not null
  )
);

create trigger opportunities_touch_updated_at
before update on public.opportunities
for each row execute function public.touch_updated_at();

create index opportunities_published_deadline_idx
  on public.opportunities (deadline_date, id)
  where status = 'published';

create index opportunities_published_category_idx
  on public.opportunities (category)
  where status = 'published';

revoke all on table public.opportunities from anon, authenticated;
grant select on table public.opportunities to anon, authenticated;
grant all on table public.opportunities to service_role;
alter table public.opportunities enable row level security;

create policy "opportunities_read_verified_published"
on public.opportunities for select to anon, authenticated
using (status = 'published' and last_verified_at is not null);

-- No INSERT, UPDATE or DELETE policy or grant for anon/authenticated.
-- The ingestion service must verify source_url and set last_verified_at before
-- publishing; deadlines and other extracted claims still require human review.
